import base64
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..zk_client import ZKClient, ZKError

_logger = logging.getLogger(__name__)

# connections open during a call, to reuse one connection for many commands: (database, device, thread) -> client
_SESSIONS = {}
# punches downloaded again before the last one received, for a device whose clock was set back
OVERLAP = timedelta(days=1)


class HrBiometricDevice(models.Model):
    _inherit = 'hr.biometric.device'

    protocol = fields.Selection(
        selection_add=[('zk', 'TCP (Pull)')],
        ondelete={'zk': lambda devices: devices._zk_uninstalled()},
        help='ADMS: the device sends its punches to Odoo over HTTP, no fixed IP address needed.\n'
             'TCP: Odoo reads the device at its IP address on port 4370; the server must reach it.')
    zk_udp = fields.Boolean(string='Use UDP', help='For the older devices that do not answer over TCP.')
    zk_timeout = fields.Integer(string='Timeout (Seconds)', default=10)
    zk_auto_download = fields.Boolean(string='Download Every 10 Minutes', default=True)
    zk_last_log_time = fields.Datetime(string='Last Punch Downloaded', readonly=True, copy=False)
    zk_error = fields.Char(string='Last Error', readonly=True, copy=False)
    zk_clear_above = fields.Integer(
        string='Clear Punches Above', default=0,
        help='When the device holds more punches than this, the scheduled download stores them all, then clears '
             'the device, which stays fast. 0: never.')

    def _zk_uninstalled(self):
        """ The TCP devices left when this module is uninstalled: archived. In SQL, the columns of this module being
            gone already. """
        if self:
            self.env.cr.execute("UPDATE hr_biometric_device SET protocol = 'adms', active = FALSE WHERE id IN %s",
                                [tuple(self.ids)])
            self.invalidate_recordset(['protocol', 'active'])

    @api.constrains('protocol', 'ip_address', 'port', 'comm_key', 'zk_timeout')
    def _check_zk(self):
        for device in self.sudo().filtered(lambda d: d.protocol == 'zk'):
            if not device.ip_address:
                raise ValidationError(self.env._('Odoo reads %s at its IP address: give it.', device.name))
            if not 0 < device.port < 65536 or device.zk_timeout <= 0:
                raise ValidationError(self.env._('The port and the timeout of %s are not valid.', device.name))
            if device.comm_key and not device.comm_key.isdigit():
                raise ValidationError(self.env._('The communication key of %s is a number.', device.name))

    @api.depends('last_contact', 'zk_error')
    def _compute_connection_state(self):
        zk_devices = self.filtered(lambda d: d.protocol == 'zk')
        for device in zk_devices:
            device.connection_state = 'offline' if device.zk_error else 'online' if device.last_contact else 'never'
        return super(HrBiometricDevice, self - zk_devices)._compute_connection_state()

    # Connection

    def _zk_client(self):
        self.ensure_one()
        return ZKClient(self.ip_address, port=self.port, timeout=self.zk_timeout,
                        password=self.sudo().comm_key or 0, udp=self.zk_udp)

    @contextmanager
    def _zk_session(self):
        """ A connection to the device, the one already open in this call if any. Errors become UserError. """
        self.ensure_one()
        key = (self.env.cr.dbname, self.id, threading.get_ident())
        if key in _SESSIONS:
            yield _SESSIONS[key]
            return
        try:
            with self._zk_client() as client:
                _SESSIONS[key] = client
                try:
                    yield client
                finally:
                    _SESSIONS.pop(key, None)
        except ZKError as error:
            self.zk_error = str(error)
            raise UserError(self.env._('%(device)s: %(error)s', device=self.name, error=error)) from error
        if self.zk_error:
            self.zk_error = False

    def _is_offline(self):
        if self.protocol == 'zk':
            return bool(self.zk_error)
        return super()._is_offline()

    # Commands: run at once on a TCP device

    def _send_command(self, command, payload, device_user=None):
        if self.protocol != 'zk':
            return super()._send_command(command, payload, device_user)
        with self._zk_session() as client:
            data = self._zk_run(client, command, device_user)
        return self._zk_done(command, payload, device_user, data)

    def _zk_done(self, command, payload, device_user=None, reply=''):
        """ Record `command`, run at once on the device. :return: the hr.biometric.command """
        record = self.env['hr.biometric.command'].create({
            'device_id': self.id, 'command': command, 'payload': payload,
            'device_user_id': device_user and device_user.id, 'state': 'sent', 'tries': 1,
            'sent_date': fields.Datetime.now()})
        record._on_reply(0, reply)
        return record

    def _zk_run(self, client, command, device_user):
        """ Run `command` on the device. :return: the reply, as text """
        if command == 'user_update':
            client.set_user(device_user.user_code, device_user.name or device_user.employee_id.name or '',
                            14 if device_user.privilege == 'admin' else 0, device_user.card or 0)
        elif command == 'user_delete':
            client.delete_user(device_user.user_code)
        elif command == 'query_users':
            users = client.get_users()
            biometrics = [{'pin': t.user_id, 'kind': 'finger', 'index': t.index, 'valid': t.valid,
                           'data': base64.b64encode(t.data).decode()} for t in client.get_templates()]
            self.env['hr.biometric.device.user']._sync_from_device(self, [
                {'pin': user.user_id, 'name': user.name, 'pri': str(user.privilege), 'card': str(user.card or '')}
                for user in users], biometrics)
            return self.env._('%(users)s users, %(fingers)s fingerprints.', users=len(users), fingers=len(biometrics))

        elif command == 'info':
            info = client.get_info()
            self._touch(info)
            return '\n'.join('%s=%s' % item for item in info.items())
        elif command == 'set_time':
            client.set_time(self._to_local(datetime.now()))
        elif command == 'reboot':
            client.restart()
        else:
            raise UserError(self.env._('The command %s is not available over TCP.', command))
        return ''

    def _push_users(self, employees):
        zk_devices = self.filtered(lambda d: d.protocol == 'zk')
        for device in zk_devices:
            with device._zk_session():
                super(HrBiometricDevice, device)._push_users(employees)
        return super(HrBiometricDevice, self - zk_devices)._push_users(employees)

    def _remove_users(self, device_users):
        for device, users in device_users.grouped('device_id').items():
            if device.protocol == 'zk':
                with device._zk_session():
                    super(HrBiometricDevice, device)._remove_users(users)
            else:
                super()._remove_users(users)
        return True

    def _read_templates(self, device_user):
        if self.protocol != 'zk':
            return super()._read_templates(device_user)
        with self._zk_session() as client:
            templates = [t for t in client.get_templates() if t.user_id == device_user.user_code and t.valid]
        return [{'index': t.index, 'data': base64.b64encode(t.data).decode()} for t in templates]

    def _write_templates(self, device_user, templates):
        if self.protocol != 'zk':
            return super()._write_templates(device_user, templates)
        user = self._target_user(device_user)
        with self._zk_session() as client:
            client.save_user_templates(user.user_code, user.name or '',
                                       [(t['index'], base64.b64decode(t['data'])) for t in templates],
                                       14 if user.privilege == 'admin' else 0, user.card or 0)
        self._zk_done('user_update', self.env._('User and %s fingerprints', len(templates)), user)
        user.fingerprint_count = max(user.fingerprint_count, len(templates))
        self.message_post(body=self.env._('%(user)s copied from %(device)s with %(count)s fingerprints.',
                                          user=user.display_name, device=device_user.device_id.name,
                                          count=len(templates)))
        return True

    def _enroll(self, device_user, index):
        if self.protocol != 'zk':
            return super()._enroll(device_user, index)
        with self._zk_session() as client:
            client.start_enroll(device_user.user_code, index)
        self._zk_done('enroll_fp', self.env._('Finger %s', index), device_user)
        return True

    def _query_logs(self, start, end):
        zk_devices = self.filtered(lambda d: d.protocol == 'zk')
        for device in zk_devices:
            device._zk_download(start, end)
        return super(HrBiometricDevice, self - zk_devices)._query_logs(start, end)

    # Punches

    def _zk_download(self, start=None, end=None):
        """ Read the punches of the device and process the new ones: from `start` to `end` (UTC), or those from
            the last one received on. A device holding more punches than its limit is then cleared: every punch it
            held is stored first, and the device is locked from the reading to the clearing so that none is lost.
            :return: the new punches """
        self.ensure_one()
        clear = bool(self.zk_clear_above) and not start and not end
        with self._zk_session() as client:
            if clear:
                with client.disabled():
                    punches = client.get_attendance()
                    logs = self._zk_store(punches)
                    if len(punches) > self.zk_clear_above:
                        client.clear_attendance()
                        self.message_post(body=self.env._(
                            '%s punches deleted from the device, after they were stored.', len(punches)))
            else:
                since = start or (self.zk_last_log_time and self.zk_last_log_time - OVERLAP)
                logs = self._zk_store(client.get_attendance(), since, end)
            info = client.get_info()
        self._touch(info)
        logs._process()
        return logs

    def _zk_store(self, punches, since=None, end=None):
        """ Store the punches read from the device not received yet, from `since` to `end` (UTC) if given.
            :return: the new punches """
        rows = []
        for punch in punches:
            timestamp = self._to_utc(punch.timestamp)
            if (since and timestamp < since) or (end and timestamp > end):
                continue
            rows.append({'user_code': punch.user_id, 'local_time': punch.timestamp, 'status': str(punch.status),
                         'verify_code': str(punch.verify), 'work_code': punch.work_code})
        logs = self.env['hr.biometric.log']._create_punches(self, rows, 'zk')
        if logs and (not self.zk_last_log_time or max(logs.mapped('timestamp')) > self.zk_last_log_time):
            self.zk_last_log_time = max(logs.mapped('timestamp'))
        return logs

    def _zk_lock(self):
        """ :return: whether this transaction got the device, no other download running on it """
        self.env.cr.execute('SELECT id FROM hr_biometric_device WHERE id = %s FOR UPDATE SKIP LOCKED', [self.id])
        return bool(self.env.cr.fetchone())

    @api.model
    def _cron_zk_download(self):
        devices = self.sudo().search([('protocol', '=', 'zk'), ('zk_auto_download', '=', True)])
        for device in devices.with_context(tracking_disable=True):
            if not device._zk_lock():
                continue
            try:
                with self.env.cr.savepoint():
                    device._zk_download()
            except UserError as error:
                # the error stays on the device; the other devices go on
                device.zk_error = str(error.args[0] if error.args else error)
                _logger.info('Biometric device %s not downloaded: %s', device.name, device.zk_error)

    # Buttons

    def action_zk_test(self):
        self.ensure_one()
        with self._zk_session() as client:
            info = client.get_info()
        self._touch(info)
        if not self.serial_number and info.get('serialnumber'):
            self.serial_number = info['serialnumber']
        return self._notify(self.env._('Connected to %(model)s %(serial)s, firmware %(firmware)s.',
                                       model=info.get('devicename') or self.name,
                                       serial=info.get('serialnumber') or '', firmware=info.get('fwversion') or ''))

    def action_zk_download(self):
        count = 0
        for device in self:
            if not device._zk_lock():
                raise UserError(self.env._('%s is being downloaded already.', device.name))
            count += len(device._zk_download())
        return self._notify(self.env._('%s new punches.', count))

    def action_zk_clear_log(self):
        """ Download the punches, then delete them from the device: never from Odoo. """
        if not self.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            raise AccessError(self.env._('Only the attendance managers clear the punches of a device.'))
        for device in self:
            device._zk_download(start=datetime(2000, 1, 1))
            with device._zk_session() as client:
                with client.disabled():
                    client.clear_attendance()
            device.message_post(body=self.env._('Punches deleted from the device, after they were downloaded.'))
        return self._notify(self.env._('The punches were downloaded, then deleted from the devices.'))
