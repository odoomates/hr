from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

STATUSES = [
    ('on_time', 'On Time'),
    ('late', 'Late'),
    ('early', 'Left Early'),
    ('late_early', 'Late and Left Early'),
    ('missing_out', 'Missing Check-Out'),
    ('working', 'At Work'),
    ('not_started', 'Not Arrived Yet'),
    ('absent', 'Absent'),
    ('leave', 'Time Off / Public Holiday'),
    ('day_off_worked', 'Worked on a Day Off'),
]
# the letters of the monthly sheet
LETTERS = {'on_time': '✓', 'late': 'L', 'early': 'E', 'late_early': 'LE', 'missing_out': 'M', 'working': 'W',
           'not_started': '', 'absent': 'A', 'leave': 'T', 'day_off_worked': 'X'}
SHEET_DAYS = 31


class HrBiometricStatusWizard(models.TransientModel):
    """ The day of each employee: on time, late, left early, missing check-out, absent, on time off or working on a day
    off, from the working schedule, the time off and the attendances. """
    _name = 'hr.biometric.status.wizard'
    _description = 'Attendance Status'

    date_from = fields.Date(string='From', required=True,
                            default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string='To', required=True, default=fields.Date.context_today)
    department_ids = fields.Many2many('hr.department', string='Departments', help='Empty: all the departments.')
    employee_ids = fields.Many2many('hr.employee', string='Employees', help='Empty: all the employees.')
    biometric_only = fields.Boolean(string='Employees on the Devices Only', default=True,
                                    help='Only the employees with a biometric ID.')
    tolerance = fields.Integer(string='Tolerance (Minutes)', default=lambda self: self.env.company.biometric_tolerance,
                               help='An arrival or a departure this many minutes off the schedule is on time.')
    status_filter = fields.Selection(STATUSES, string='Only', help='Show only the days of this status.')
    line_ids = fields.One2many('hr.biometric.day', 'wizard_id')

    @api.constrains('date_from', 'date_to', 'tolerance')
    def _check_values(self):
        for wizard in self:
            if wizard.date_to < wizard.date_from:
                raise ValidationError(_('The period ends after it starts.'))
            if wizard.tolerance < 0:
                raise ValidationError(_('The tolerance cannot be negative.'))

    def _employees(self):
        if self.employee_ids:
            return self.employee_ids
        domain = [('company_id', 'in', self.env.companies.ids), ('resource_calendar_id', '!=', False)]
        if self.department_ids:
            domain.append(('department_id', 'child_of', self.department_ids.ids))
        if self.biometric_only:
            domain.append(('biometric_code', '!=', False))
        return self.env['hr.employee'].search(domain)

    def _days_of(self, employee):
        """ :return: {date: values of hr.biometric.day} of `employee` over the period. Days off without attendance
            and days to come are left out. """
        calendar = employee.resource_calendar_id
        if not calendar:
            return {}
        tz = pytz.timezone(employee.tz or 'UTC')
        start = tz.localize(datetime.combine(self.date_from, time.min))
        end = tz.localize(datetime.combine(self.date_to, time.max))
        resources = employee.resource_id
        resource = employee.resource_id.id
        work = {}
        for interval_start, interval_stop, _meta in calendar._work_intervals_batch(
                start, end, resources=resources, tz=tz)[resource]:
            day = interval_start.astimezone(tz).date()
            first, last, hours = work.get(day, (interval_start, interval_stop, 0.0))
            work[day] = (min(first, interval_start), max(last, interval_stop),
                         hours + (interval_stop - interval_start).total_seconds() / 3600)
        planned = {interval_start.astimezone(tz).date() for interval_start, _stop, _meta in
                   calendar._attendance_intervals_batch(start, end, resources=resources, tz=tz)[resource]}
        attendances = {}
        for attendance in self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start.astimezone(pytz.utc).replace(tzinfo=None)),
                ('check_in', '<=', end.astimezone(pytz.utc).replace(tzinfo=None))], order='check_in'):
            attendances.setdefault(pytz.utc.localize(attendance.check_in).astimezone(tz).date(), []).append(attendance)
        now = pytz.utc.localize(fields.Datetime.now()).astimezone(tz)
        tolerance = timedelta(minutes=self.tolerance)
        days = {}
        day = self.date_from
        while day <= self.date_to:
            vals = self._day_vals(day, work.get(day), day in planned, attendances.get(day, []), now, tolerance, tz)
            if vals:
                days[day] = vals
            day += timedelta(days=1)
        return days

    @staticmethod
    def _day_vals(day, work, planned, attendances, now, tolerance, tz):
        """ :return: the values of one day, or None for a day off without attendance or a day to come """
        if day > now.date():
            return None
        vals = {}
        if attendances:
            first_in = pytz.utc.localize(attendances[0].check_in).astimezone(tz)
            outs = [a.check_out for a in attendances if a.check_out]
            vals.update(first_in=attendances[0].check_in, last_out=max(outs) if outs else False,
                        worked_hours=sum(a.worked_hours for a in attendances))
        if not work:
            if attendances:
                vals['status'] = 'day_off_worked'
            elif planned:
                vals['status'] = 'leave'
            else:
                return None
            return vals
        expected_start, expected_end, hours = work
        vals.update(expected_start=expected_start.astimezone(pytz.utc).replace(tzinfo=None),
                    expected_end=expected_end.astimezone(pytz.utc).replace(tzinfo=None), expected_hours=hours)
        if not attendances:
            vals['status'] = 'not_started' if day == now.date() and now < expected_start + tolerance else 'absent'
            return vals
        late = first_in > expected_start + tolerance
        if late:
            vals['late_minutes'] = (first_in - expected_start).total_seconds() / 60
        if any(not a.check_out for a in attendances):
            vals['status'] = 'working' if day == now.date() else 'missing_out'
            return vals
        last_out = pytz.utc.localize(vals['last_out']).astimezone(tz)
        early = last_out < expected_end - tolerance
        if early:
            vals['early_minutes'] = (expected_end - last_out).total_seconds() / 60
        vals['status'] = 'late_early' if late and early else 'late' if late else 'early' if early else 'on_time'
        return vals

    def _compute_lines(self):
        self.ensure_one()
        self.line_ids.unlink()
        lines = []
        for employee in self._employees():
            for day, vals in sorted(self._days_of(employee).items()):
                if self.status_filter and vals['status'] != self.status_filter:
                    continue
                lines.append(dict(vals, wizard_id=self.id, employee_id=employee.id, date=day,
                                  department_id=employee.department_id.id, company_id=employee.company_id.id))
        return self.env['hr.biometric.day'].create(lines)

    def action_analyze(self):
        self._compute_lines()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attendance Status from %(start)s to %(end)s', start=self.date_from, end=self.date_to),
            'res_model': 'hr.biometric.day',
            'view_mode': 'tree,pivot,graph',
            'domain': [('wizard_id', '=', self.id)],
            'context': {'create': False},
        }

    def action_print_sheet(self):
        if (self.date_to - self.date_from).days >= SHEET_DAYS:
            raise UserError(_('The monthly sheet holds %s days at most.', SHEET_DAYS))
        self.status_filter = False
        self._compute_lines()
        return self.env.ref('om_hr_biometric.action_report_monthly_sheet').report_action(self)

    @api.model
    def action_today(self):
        """ The board of today: who is at work, late, not arrived yet or absent. """
        today = fields.Date.context_today(self)
        wizard = self.create({'date_from': today, 'date_to': today})
        wizard._compute_lines()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Today'),
            'res_model': 'hr.biometric.day',
            'view_mode': 'kanban,tree',
            'domain': [('wizard_id', '=', wizard.id)],
            'context': {'create': False, 'group_by': 'status'},
        }

    def _sheet(self):
        """ :return: (dates, rows) of the monthly sheet: rows of (employee, [letter per date], totals) """
        self.ensure_one()
        dates = [self.date_from + timedelta(days=index) for index in range((self.date_to - self.date_from).days + 1)]
        rows = []
        by_employee = {}
        for line in self.line_ids.sorted(lambda line: (line.employee_id.name, line.date)):
            by_employee[line.employee_id] = by_employee.get(line.employee_id, line.browse()) | line
        for employee, lines in by_employee.items():
            by_date = {line.date: line for line in lines}
            statuses = [line.status for line in lines]
            rows.append((employee, [LETTERS.get(by_date[day].status, '') if day in by_date else '' for day in dates], {
                'present': sum(1 for s in statuses if s in ('on_time', 'late', 'early', 'late_early', 'missing_out',
                                                             'working', 'day_off_worked')),
                'absent': statuses.count('absent'),
                'late': sum(1 for s in statuses if s in ('late', 'late_early')),
                'hours': sum(lines.mapped('worked_hours')),
            }))
        return dates, rows


class HrBiometricDay(models.TransientModel):
    """ The day of an employee. """
    _name = 'hr.biometric.day'
    _description = 'Attendance Day'
    _order = 'date, employee_id'
    _rec_name = 'employee_id'

    wizard_id = fields.Many2one('hr.biometric.status.wizard', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True, readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    date = fields.Date(readonly=True)
    status = fields.Selection(STATUSES, readonly=True)
    expected_start = fields.Datetime(readonly=True)
    expected_end = fields.Datetime(readonly=True)
    expected_hours = fields.Float(string='Hours Expected', readonly=True, group_operator='sum')
    first_in = fields.Datetime(string='First Check-In', readonly=True)
    last_out = fields.Datetime(string='Last Check-Out', readonly=True)
    worked_hours = fields.Float(readonly=True, group_operator='sum')
    late_minutes = fields.Float(readonly=True, group_operator='sum')
    early_minutes = fields.Float(readonly=True, group_operator='sum')
    image = fields.Binary(related='employee_id.avatar_128')

    def action_open_attendances(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.employee_id.name,
            'res_model': 'hr.attendance',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.employee_id.id)],
            'context': {'default_employee_id': self.employee_id.id},
        }
