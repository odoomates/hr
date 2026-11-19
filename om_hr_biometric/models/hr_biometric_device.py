import ipaddress
from datetime import datetime, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.base.models.res_partner import _tz_get

from .. import adms

MODES = [
    ('alternate', 'Alternate'),
    ('status_code', 'Status Codes'),
    ('in_only', 'Check-In Only'),
    ('out_only', 'Check-Out Only'),
]
DEFAULT_STATUS_CODES = [
    ('0', 'check_in'), ('1', 'check_out'), ('2', 'break_out'), ('3', 'break_in'), ('4', 'overtime_in'),
    ('5', 'overtime_out'),
]
# a device is online when it called within this delay (it calls about every 10 seconds)
ONLINE_DELAY = timedelta(minutes=5)
# last contact is written at most this often
CONTACT_DELAY = timedelta(seconds=30)


class HrBiometricDevice(models.Model):
    """ A biometric time clock (ZKTeco, eSSL...): where its punches come from, how they become check-ins and
    check-outs, and the users enrolled on it. """
    _name = 'hr.biometric.device'
    _description = 'Biometric Device'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True,
                                 tracking=True)
    protocol = fields.Selection([('adms', 'ADMS (Push)')], required=True, default='adms', tracking=True,
                                help='ADMS: the device sends its punches to Odoo over HTTP, no fixed IP address '
                                     'needed.')
    serial_number = fields.Char(copy=False, tracking=True,
                                help='Serial number of the device (Menu > System Info > Device Info).')
    ip_address = fields.Char(string='IP Address')
    port = fields.Integer(default=4370)
    comm_key = fields.Char(string='Communication Key', copy=False,
                           groups='hr_attendance.group_hr_attendance_manager')
    allowed_ips = fields.Char(string='Allowed IP Addresses',
                              help='IP addresses or networks (e.g. 203.0.113.7, 10.0.0.0/24), comma separated, the '
                                   'device may call from. Empty: any.')
    timezone = fields.Selection(_tz_get, required=True, default=lambda self: self._default_timezone(),
                                help='Timezone of the clock of the device.')
    attendance_mode = fields.Selection(
        MODES, required=True, default='alternate', tracking=True,
        help='Alternate: a punch checks in, the next one checks out.\n'
             'Status Codes: the status the employee selects on the device (check in, check out, break...); a '
             'punch without a known status alternates.\n'
             'Check-In Only / Check-Out Only: for separate entry and exit devices.')
    duplicate_window = fields.Integer(string='Repeated Punches (Minutes)', default=1,
                                      help='A punch of the same employee within this many minutes of the previous '
                                           'one is ignored.')
    status_code_ids = fields.One2many('hr.biometric.status.code', 'device_id', string='Status Codes', copy=True)
    user_ids = fields.One2many('hr.biometric.device.user', 'device_id', string='Device Users')
    last_contact = fields.Datetime(readonly=True, copy=False)
    connection_state = fields.Selection([('never', 'Never Connected'), ('online', 'Online'), ('offline', 'Offline')],
                                        compute='_compute_connection_state')
    attlog_stamp = fields.Char(readonly=True, copy=False)
    operlog_stamp = fields.Char(readonly=True, copy=False)
    device_model = fields.Char(readonly=True, copy=False)
    firmware_version = fields.Char(readonly=True, copy=False)
    platform = fields.Char(readonly=True, copy=False)
    mac_address = fields.Char(string='MAC Address', readonly=True, copy=False)
    device_user_count = fields.Integer(string='Users on Device', readonly=True, copy=False)
    device_fingerprint_count = fields.Integer(string='Fingerprints on Device', readonly=True, copy=False)
    device_face_count = fields.Integer(string='Faces on Device', readonly=True, copy=False)
    device_log_count = fields.Integer(string='Punches on Device', readonly=True, copy=False)
    log_count = fields.Integer(compute='_compute_counts')
    unmapped_count = fields.Integer(compute='_compute_counts')
    user_count = fields.Integer(compute='_compute_counts')
    pending_command_count = fields.Integer(compute='_compute_counts')
    error_count = fields.Integer(string='Punches in Error', compute='_compute_counts')
    failed_command_count = fields.Integer(string='Failed Commands', compute='_compute_counts')

    _sql_constraints = [
        ('serial_number_uniq', 'UNIQUE(serial_number)', 'A device with this serial number already exists.'),
    ]

    @api.model
    def _default_timezone(self):
        return self.env.company.partner_id.tz or self.env.user.tz or 'UTC'

    @api.depends('last_contact')
    def _compute_connection_state(self):
        now = fields.Datetime.now()
        for device in self:
            if not device.last_contact:
                device.connection_state = 'never'
            else:
                device.connection_state = 'online' if now - device.last_contact <= ONLINE_DELAY else 'offline'

    def _compute_counts(self):
        counts = {}
        for model, domain, key in [
            ('hr.biometric.log', [], 'log_count'),
            ('hr.biometric.log', [('state', '=', 'unmapped')], 'unmapped_count'),
            ('hr.biometric.device.user', [], 'user_count'),
            ('hr.biometric.command', [('state', 'in', ('pending', 'sent'))], 'pending_command_count'),
            ('hr.biometric.log', [('state', '=', 'error')], 'error_count'),
            ('hr.biometric.command', [('state', '=', 'failed')], 'failed_command_count'),
        ]:
            for group in self.env[model].read_group(domain + [('device_id', 'in', self.ids)], ['device_id'],
                                                    ['device_id']):
                counts[group['device_id'][0], key] = group['device_id_count']
        for device in self:
            for key in ('log_count', 'unmapped_count', 'user_count', 'pending_command_count', 'error_count',
                        'failed_command_count'):
                device[key] = counts.get((device.id, key), 0)

    @api.constrains('protocol', 'serial_number', 'active')
    def _check_serial_number(self):
        for device in self:
            if device.protocol == 'adms' and device.active and not device.serial_number:
                raise ValidationError(_('Device %s sends its punches with ADMS: give its serial number.',
                                                 device.name))

    @api.constrains('allowed_ips')
    def _check_allowed_ips(self):
        for device in self:
            try:
                device._allowed_networks()
            except ValueError as error:
                raise ValidationError(_('The allowed IP addresses of %(device)s are not valid: %(error)s',
                                                 device=device.name, error=error)) from error

    @api.constrains('duplicate_window')
    def _check_duplicate_window(self):
        if any(device.duplicate_window < 0 for device in self):
            raise ValidationError(_('The repeated punches window cannot be negative.'))

    @api.model_create_multi
    def create(self, vals_list):
        devices = super().create(vals_list)
        for device in devices.filtered(lambda d: not d.status_code_ids):
            device.status_code_ids = [fields.Command.create({'code': code, 'action': action})
                                      for code, action in DEFAULT_STATUS_CODES]
        return devices

    # Time

    def _to_utc(self, local_time):
        """ :return: `local_time`, the naive time of the clock of the device, in UTC (naive). The hour repeated
            when the clocks go back takes its first occurrence; a time skipped when they go forward is read as
            summer time. """
        self.ensure_one()
        local = pytz.timezone(self.timezone).localize(local_time, is_dst=True)
        return local.astimezone(pytz.utc).replace(tzinfo=None)

    def _to_local(self, utc_time):
        self.ensure_one()
        return pytz.utc.localize(utc_time).astimezone(pytz.timezone(self.timezone)).replace(tzinfo=None)

    # Punches

    def _punch_direction(self, status):
        """ :return: 'in', 'out', 'toggle' (in if no attendance is open, else out) or 'ignore', for a punch of
            this device with `status`. Hook for other modes. """
        self.ensure_one()
        if self.attendance_mode == 'in_only':
            return 'in'
        if self.attendance_mode == 'out_only':
            return 'out'
        if self.attendance_mode == 'status_code':
            code = self.status_code_ids.filtered(lambda c: c.code == (status or '').strip())[:1]
            if code:
                return code._direction()
        return 'toggle'

    # Connection

    def _allowed_networks(self):
        self.ensure_one()
        return [ipaddress.ip_network(part.strip(), strict=False)
                for part in (self.allowed_ips or '').split(',') if part.strip()]

    def _accepts_ip(self, address):
        """ :return: whether the device may call from `address`. """
        self.ensure_one()
        networks = self._allowed_networks()
        if not networks:
            return True
        try:
            address = ipaddress.ip_address(address or '')
        except ValueError:
            return False
        return any(address in network for network in networks)

    def _touch(self, info=None):
        """ Record a contact of the device, and the device information it sends (dict from adms.parse_info). """
        self.ensure_one()
        vals = self._info_vals(info or {})
        now = fields.Datetime.now()
        if not self.last_contact or now - self.last_contact >= CONTACT_DELAY:
            vals['last_contact'] = now
        vals = {key: value for key, value in vals.items() if self[key] != value}
        if vals:
            self.write(vals)

    def _info_vals(self, info):
        def number(key):
            try:
                return int(info[key])
            except (KeyError, ValueError):
                return None
        vals = {}
        for field, key in [('device_model', 'devicename'), ('firmware_version', 'fwversion'),
                           ('platform', 'platform'), ('mac_address', 'mac'), ('ip_address', 'ipaddress')]:
            if info.get(key):
                vals[field] = info[key]
        for field, key in [('device_user_count', 'usercount'), ('device_fingerprint_count', 'fpcount'),
                           ('device_face_count', 'facecount'), ('device_log_count', 'transactioncount')]:
            if number(key) is not None:
                vals[field] = number(key)
        return vals

    # Commands (ADMS: queued until the device calls; other protocols override them)

    def _send_command(self, command, payload, device_user=None):
        """ Send `payload` to the device. ADMS queues it for the next call of the device. Hook for other
            protocols. :return: the hr.biometric.command """
        self.ensure_one()
        return self.env['hr.biometric.command'].create({
            'device_id': self.id,
            'command': command,
            'payload': payload,
            'device_user_id': device_user and device_user.id,
        })

    def _push_users(self, employees):
        """ Enroll `employees` on the devices, or update their name: gives a biometric ID to those without. """
        employees._assign_biometric_code()
        DeviceUser = self.env['hr.biometric.device.user']
        for device in self:
            for employee in employees.filtered(lambda e: e.company_id == device.company_id):
                user = DeviceUser.search([('device_id', '=', device.id),
                                          ('user_code', '=', employee.biometric_code)], limit=1)
                if user:
                    user.write({'employee_id': employee.id, 'name': employee.name, 'state': 'to_push'})
                else:
                    user = DeviceUser.create({'device_id': device.id, 'user_code': employee.biometric_code,
                                              'name': employee.name, 'employee_id': employee.id,
                                              'state': 'to_push'})
                device._send_command('user_update', user._update_command(), user)

    def _remove_users(self, device_users):
        """ Remove `device_users` from their devices; they are deleted once the device confirms. """
        for user in device_users:
            user.state = 'to_delete'
            user.device_id._send_command('user_delete', adms.user_delete_command(user.user_code), user)

    def _read_templates(self, device_user):
        """ :return: the fingerprint templates of `device_user` (dicts index, data in base64) to copy it: those kept
            in Odoo. Hook for the protocols that read them from the device. """
        self.ensure_one()
        return device_user._templates()

    def _target_user(self, device_user):
        """ :return: the user of this device standing for `device_user` of another device, to send """
        self.ensure_one()
        vals = {'name': device_user.name or device_user.employee_id.name, 'privilege': device_user.privilege,
                'card': device_user.card, 'employee_id': device_user.employee_id.id, 'state': 'to_push'}
        user = self.user_ids.filtered(lambda u: u.user_code == device_user.user_code)
        if user:
            user.write(vals)
            return user
        return self.env['hr.biometric.device.user'].create(dict(vals, device_id=self.id,
                                                                user_code=device_user.user_code))

    def _write_templates(self, device_user, templates):
        """ Enroll `device_user` of another device on this one, with its fingerprint `templates`. Hook for other
            protocols. """
        self.ensure_one()
        user = self._target_user(device_user)
        self._send_command('user_update', user._update_command(), user)
        for template in templates:
            self._send_command('template_update',
                               adms.template_update_command(user.user_code, template['index'], template['data']), user)
        self.message_post(body=_('%(user)s copied from %(device)s with %(count)s fingerprints.',
                                          user=user.display_name, device=device_user.device_id.name,
                                          count=len(templates)))

    def _enroll(self, device_user, index):
        """ Start the enrollment of finger `index` of `device_user` on the device. Hook for other protocols. """
        self.ensure_one()
        self._send_command('enroll_fp', adms.enroll_command(device_user.user_code, index), device_user)

    def _query_logs(self, start, end):
        """ Ask the devices for their punches from `start` to `end` (UTC). """
        for device in self:
            device._send_command('query_logs', adms.query_logs_command(device._to_local(start),
                                                                       device._to_local(end)))

    def action_reboot(self):
        for device in self:
            device._send_command('reboot', 'REBOOT')
        return self._notify(_('The devices restart at their next contact.'))

    def action_query_users(self):
        for device in self:
            device._send_command('query_users', 'DATA QUERY USERINFO')
        return self._notify(_('The devices send their users at their next contact.'))

    def action_query_info(self):
        for device in self:
            device._send_command('info', 'INFO')
        return self._notify(_('The devices send their information at their next contact.'))

    def action_set_time(self):
        for device in self:
            device._send_command('set_time', adms.set_time_command(device._to_local(datetime.now())))
        return self._notify(_('The clocks of the devices are set at their next contact.'))

    def _notify(self, message):
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'message': message, 'type': 'success', 'sticky': False}}

    # ADMS

    def _adms_handshake(self):
        self.ensure_one()
        offset = pytz.timezone(self.timezone).utcoffset(datetime.now())
        return adms.handshake(self.serial_number, self.attlog_stamp, self.operlog_stamp,
                              adms.timezone_option(offset))

    def _adms_attlog(self, body, stamp=None):
        """ Punches uploaded by the device. :return: the number of lines read """
        self.ensure_one()
        punches = adms.parse_attlog(body)
        logs = self.env['hr.biometric.log']._create_punches(self, punches, 'adms')
        logs._process()
        if stamp and stamp != self.attlog_stamp:
            self.attlog_stamp = stamp
        return len(punches)

    def _adms_operlog(self, body, stamp=None):
        """ Users and biometric templates uploaded by the device. :return: the number of users and templates """
        self.ensure_one()
        users, biometrics = adms.parse_operlog(body)
        self.env['hr.biometric.device.user']._sync_from_device(self, users, biometrics)
        if stamp and stamp != self.operlog_stamp:
            self.operlog_stamp = stamp
        return len(users) + len(biometrics)

    def _adms_command_lines(self, limit=20):
        """ :return: the commands to send to the device as it asks for them, marked as sent. """
        self.ensure_one()
        commands = self.env['hr.biometric.command']._to_send(self, limit)
        commands._mark_sent()
        return ''.join(command._adms_line() + '\n' for command in commands)

    def _adms_replies(self, body):
        self.ensure_one()
        Command = self.env['hr.biometric.command']
        for command_id, code, data in adms.parse_command_replies(body):
            command = Command.search([('id', '=', command_id), ('device_id', '=', self.id)])
            if command:
                command._on_reply(code, data)

    # Views

    def _action_open(self, model, name, domain=None, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': 'list,form',
            'domain': [('device_id', '=', self.id)] + (domain or []),
            'context': dict({'default_device_id': self.id}, **(context or {})),
        }

    def action_view_logs(self):
        return self._action_open('hr.biometric.log', _('Punches'))

    def action_view_unmapped(self):
        return self._action_open('hr.biometric.log', _('Unmapped Punches'), [('state', '=', 'unmapped')])

    def action_view_errors(self):
        return self._action_open('hr.biometric.log', _('Punches in Error'), [('state', '=', 'error')])

    def action_view_users(self):
        return self._action_open('hr.biometric.device.user', _('Device Users'))

    def action_view_commands(self):
        return self._action_open('hr.biometric.command', _('Commands'), context={'create': False})

    def action_open_download(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Download Punches'),
            'res_model': 'hr.biometric.download',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_device_ids': self.ids},
        }

    def action_open_export(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Employees'),
            'res_model': 'hr.biometric.export',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_device_ids': self.ids},
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_punches(self):
        if self.env['hr.biometric.log'].sudo().search([('device_id', 'in', self.ids)], limit=1):
            raise UserError(_('A device with punches cannot be deleted: archive it.'))
