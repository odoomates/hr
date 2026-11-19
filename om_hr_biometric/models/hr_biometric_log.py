from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_datetime

from .. import adms
from .common import group_records

VERIFY_TYPES = [('finger', 'Fingerprint'), ('face', 'Face'), ('card', 'Card'), ('password', 'Password'),
                ('palm', 'Palm'), ('other', 'Other')]
# verify modes the devices send with a punch
VERIFY_CODES = {'0': 'password', '1': 'finger', '2': 'card', '3': 'password', '4': 'card', '15': 'face',
                '25': 'palm'}


class HrBiometricLog(models.Model):
    """ A punch, as the device sent it. Never changed: processed into the attendances, again if needed. """
    _name = 'hr.biometric.log'
    _description = 'Biometric Punch'
    _order = 'timestamp desc, id desc'
    _rec_name = 'timestamp'

    device_id = fields.Many2one('hr.biometric.device', required=True, ondelete='restrict', index=True,
                                readonly=True)
    company_id = fields.Many2one(related='device_id.company_id', store=True, index=True)
    user_code = fields.Char(string='User ID', required=True, index=True, readonly=True)
    device_user_id = fields.Many2one('hr.biometric.device.user', ondelete='set null', readonly=True)
    employee_id = fields.Many2one('hr.employee', index=True, readonly=True)
    timestamp = fields.Datetime(string='Time', required=True, index=True, readonly=True)
    local_time = fields.Char(string='Device Time', readonly=True, help='The time on the clock of the device.')
    status = fields.Char(readonly=True, help='The status selected on the device (check in, check out...).')
    verify_code = fields.Char(readonly=True)
    verify_type = fields.Selection(VERIFY_TYPES, compute='_compute_verify_type', store=True)
    work_code = fields.Char(readonly=True)
    source = fields.Selection([('adms', 'ADMS'), ('import', 'Import')], required=True, default='import',
                              readonly=True)
    punch = fields.Selection([('in', 'Check In'), ('out', 'Check Out')], readonly=True)
    state = fields.Selection([
        ('new', 'To Process'),
        ('done', 'Done'),
        ('ignored', 'Ignored'),
        ('unmapped', 'Unknown User'),
        ('error', 'Error'),
    ], required=True, default='new', index=True, readonly=True)
    message = fields.Char(readonly=True)
    attendance_id = fields.Many2one('hr.attendance', ondelete='set null', index=True, readonly=True)

    _sql_constraints = [
        ('punch_uniq', 'UNIQUE(device_id, user_code, timestamp)', 'This punch was already received from this device.'),
    ]

    @api.depends('verify_code')
    def _compute_verify_type(self):
        for log in self:
            log.verify_type = VERIFY_CODES.get(log.verify_code, 'other') if log.verify_code else False

    @api.model
    def _create_punches(self, device, punches, source):
        """ Store the punches of `device` not received yet: `punches` are dicts (user_code, local_time naive in
            the timezone of the device, status, verify_code, work_code). :return: the new punches, to process """
        rows = {}
        for punch in punches:
            timestamp = device._to_utc(punch['local_time'])
            rows.setdefault((punch['user_code'], timestamp), punch)
        if not rows:
            return self.browse()
        timestamps = [timestamp for _code, timestamp in rows]
        known = {(log.user_code, log.timestamp) for log in self.sudo().search([
            ('device_id', '=', device.id), ('timestamp', '>=', min(timestamps)),
            ('timestamp', '<=', max(timestamps)),
        ])}
        return self.sudo().create([{
            'device_id': device.id,
            'user_code': code,
            'timestamp': timestamp,
            'local_time': punch['local_time'].strftime(adms.DATETIME_FORMAT),
            'status': punch.get('status') or False,
            'verify_code': punch.get('verify_code') or False,
            'work_code': punch.get('work_code') or False,
            'source': source,
        } for (code, timestamp), punch in rows.items() if (code, timestamp) not in known])

    # Processing

    def _process(self):
        """ Turn the punches into check-ins and check-outs, employee by employee, in the order of time. A punch that
            fails keeps its error; the others go on. """
        logs = self.sudo().filtered(lambda log: log.state in ('new', 'unmapped'))
        logs._find_employees()
        logs = logs.filtered(lambda log: log.state == 'new').sorted(lambda log: (log.timestamp, log.id))
        for log in logs:
            try:
                with self.env.cr.savepoint():
                    log._process_one()
            except (UserError, ValidationError) as error:
                log.write({'state': 'error', 'message': str(error.args[0] if error.args else error)})
        return True

    def _find_employees(self):
        """ Set the device user and the employee of the punches; those of no employee are unmapped. """
        for (device, code), logs in group_records(self, lambda log: (log.device_id, log.user_code)).items():
            user = self.env['hr.biometric.device.user'].search([('device_id', '=', device.id),
                                                               ('user_code', '=', code)], limit=1)
            employee = user.employee_id or self.env['hr.employee'].search([
                ('biometric_code', '=', code), ('company_id', 'in', (device.company_id.id, False)),
            ], limit=1)
            if employee:
                logs.write({'device_user_id': user.id, 'employee_id': employee.id, 'state': 'new',
                            'message': False})
            else:
                logs.write({'device_user_id': user.id, 'employee_id': False, 'state': 'unmapped',
                            'message': _('No employee has the user ID %s on this device.', code)})

    def _process_one(self):
        self.ensure_one()
        if self._is_repeated():
            return self._skip(_('Repeated punch.'))
        punch = self.device_id._punch_direction(self.status)
        if punch == 'ignore':
            return self._skip(_('The status %s is ignored.', self.status))
        last = self._last_attendance()
        open_ok = bool(last and not last.check_out and not self._is_forgotten(last))
        if punch == 'toggle':
            punch = self._toggle(last, open_ok)
        if punch == 'in':
            return self._check_in(last, open_ok)
        return self._check_out(last, open_ok)

    def _is_forgotten(self, attendance):
        """ :return: whether the open `attendance` was never checked out, this punch starting a new one. Hook. """
        return self.timestamp - attendance.check_in > self._max_shift()

    def _toggle(self, last, open_ok):
        """ :return: 'in' or 'out', for a punch that alternates; `open_ok`: an attendance is open. Hook. """
        return 'out' if open_ok else 'in'

    def _max_shift(self):
        return timedelta(hours=self.device_id.company_id.biometric_max_shift or 16.0)

    def _is_repeated(self):
        window = timedelta(minutes=self.device_id.duplicate_window)
        return bool(self.search([
            ('employee_id', '=', self.employee_id.id), ('state', '=', 'done'), ('id', '!=', self.id),
            ('timestamp', '>=', self.timestamp - window), ('timestamp', '<=', self.timestamp),
        ], limit=1))

    def _attendance_domain(self):
        return [('employee_id', '=', self.employee_id.id)]

    def _last_attendance(self):
        return self.env['hr.attendance'].search(self._attendance_domain() + [('check_in', '<=', self.timestamp)],
                                                order='check_in desc', limit=1)

    def _next_attendance(self):
        return self.env['hr.attendance'].search(self._attendance_domain() + [('check_in', '>', self.timestamp)],
                                                order='check_in', limit=1)

    def _skip(self, message):
        self.write({'state': 'ignored', 'message': message})

    def _fail(self, message):
        self.write({'state': 'error', 'message': message})

    def _done(self, punch, attendance, message=False):
        self.write({'state': 'done', 'punch': punch, 'attendance_id': attendance.id, 'message': message})

    def _close_forgotten(self, attendance):
        """ `attendance` was never checked out: closed at its check-in, to be reviewed. """
        # hr.attendance has no chatter in 15.0: the flag tells it
        attendance.write({'check_out': attendance.check_in, 'biometric_review': True})

    def _check_in(self, last, open_ok):
        if open_ok:
            return self._skip(_('Already checked in since %s.', format_datetime(self.env, last.check_in)))
        if last and (last.check_in == self.timestamp or (last.check_out and last.check_out > self.timestamp)):
            return self._skip(_('Within an existing attendance.'))
        if self._next_attendance():
            raise UserError(_('There are later attendances: process the period again.'))
        if last and not last.check_out:
            self._close_forgotten(last)
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_id.id,
            'check_in': self.timestamp,
            'in_device_id': self.device_id.id,
        })
        return self._done('in', attendance)

    def _check_out(self, last, open_ok):
        if open_ok:
            last.write({'check_out': self.timestamp, 'out_device_id': self.device_id.id})
            return self._done('out', last)
        if last and not last.check_out:
            self._close_forgotten(last)
            return self._fail(_('Check-out without a check-in.'))
        if last and last.check_out >= self.timestamp:
            return self._skip(_('Within an existing attendance.'))
        if last and last.in_device_id and self.timestamp - last.check_in <= self._max_shift():
            # a later check-out of the same shift: the last one counts
            last.write({'check_out': self.timestamp, 'out_device_id': self.device_id.id})
            return self._done('out', last, _('Later check-out of the same attendance.'))
        return self._fail(_('Check-out without a check-in.'))

    @api.model
    def _reprocess(self, date_from, date_to, devices=None, employees=None):
        """ Process again the punches from `date_from` to `date_to` (dates, in UTC): the attendances the devices
            created in the period are deleted and the punches replayed. """
        domain = [('timestamp', '>=', datetime.combine(date_from, time.min)),
                  ('timestamp', '<', datetime.combine(date_to + timedelta(days=1), time.min)),
                  ('state', '!=', 'unmapped')]
        if devices:
            domain.append(('device_id', 'in', devices.ids))
        if employees:
            domain.append(('employee_id', 'in', employees.ids))
        logs = self.sudo().search(domain)
        attendances = logs.attendance_id.filtered('in_device_id')
        logs |= self.sudo().search([('attendance_id', 'in', attendances.ids)])
        logs.write({'state': 'new', 'punch': False, 'attendance_id': False, 'message': False})
        attendances.unlink()
        logs._process()
        return logs

    @api.model
    def _cron_process(self):
        self.sudo().search([('state', '=', 'new')], order='timestamp, id', limit=5000)._process()

    def action_process(self):
        self.filtered(lambda log: log.state in ('new', 'unmapped', 'error')).write({'state': 'new'})
        self._process()
