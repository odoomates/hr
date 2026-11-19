from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrBiometricAbsenceWizard(models.TransientModel):
    """ The working days of the employees without attendance: their working schedule, less the time off and the
    public holidays, less the days they attended. """
    _name = 'hr.biometric.absence.wizard'
    _description = 'Absence Report'

    date_from = fields.Date(string='From', required=True,
                            default=lambda self: fields.Date.today() - timedelta(days=7))
    date_to = fields.Date(string='To', required=True, default=lambda self: fields.Date.today() - timedelta(days=1))
    department_ids = fields.Many2many('hr.department', string='Departments', help='Empty: all the departments.')
    employee_ids = fields.Many2many('hr.employee', string='Employees', help='Empty: all the employees.')
    biometric_only = fields.Boolean(string='Employees on the Devices Only', default=True,
                                    help='Only the employees with a biometric ID.')
    line_ids = fields.One2many('hr.biometric.absence', 'wizard_id')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(wizard.date_to < wizard.date_from for wizard in self):
            raise ValidationError(self.env._('The period ends after it starts.'))

    def _employees(self):
        if self.employee_ids:
            return self.employee_ids
        domain = [('company_id', 'in', self.env.companies.ids), ('resource_calendar_id', '!=', False)]
        if self.department_ids:
            domain.append(('department_id', 'child_of', self.department_ids.ids))
        if self.biometric_only:
            domain.append(('biometric_code', '!=', False))
        return self.env['hr.employee'].search(domain)

    def _absences(self, employee):
        """ :return: {date: hours expected} of the working days of `employee` in the period without attendance """
        calendar = employee.resource_calendar_id
        if not calendar:
            return {}
        tz = pytz.timezone(employee.tz or calendar.tz or 'UTC')
        last = min(self.date_to, fields.Date.context_today(self) - timedelta(days=1))
        if last < self.date_from:
            return {}
        start = tz.localize(datetime.combine(self.date_from, time.min))
        end = tz.localize(datetime.combine(last, time.max))
        intervals = calendar._work_intervals_batch(start, end, resources=employee.resource_id, tz=tz)
        expected = {}
        for interval_start, interval_stop, _meta in intervals[employee.resource_id.id]:
            day = interval_start.astimezone(tz).date()
            expected[day] = expected.get(day, 0.0) + (interval_stop - interval_start).total_seconds() / 3600
        utc_start = start.astimezone(pytz.utc).replace(tzinfo=None)
        utc_end = end.astimezone(pytz.utc).replace(tzinfo=None)
        attended = {pytz.utc.localize(attendance.check_in).astimezone(tz).date()
                    for attendance in self.env['hr.attendance'].search([
                        ('employee_id', '=', employee.id), ('check_in', '>=', utc_start),
                        ('check_in', '<=', utc_end)])}
        return {day: hours for day, hours in expected.items() if day not in attended and hours > 0}

    def action_compute(self):
        self.ensure_one()
        self.line_ids.unlink()
        lines = []
        for employee in self._employees():
            for day, hours in sorted(self._absences(employee).items()):
                lines.append({'wizard_id': self.id, 'employee_id': employee.id, 'date': day,
                              'department_id': employee.department_id.id, 'company_id': employee.company_id.id,
                              'expected_hours': hours})
        self.env['hr.biometric.absence'].create(lines)
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Absences from %(start)s to %(end)s', start=self.date_from, end=self.date_to),
            'res_model': 'hr.biometric.absence',
            'view_mode': 'list,pivot',
            'domain': [('wizard_id', '=', self.id)],
            'context': {'create': False},
        }


class HrBiometricAbsence(models.TransientModel):
    """ A working day without attendance. """
    _name = 'hr.biometric.absence'
    _description = 'Absence'
    _order = 'date, employee_id'
    _rec_name = 'employee_id'

    wizard_id = fields.Many2one('hr.biometric.absence.wizard', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True, readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    date = fields.Date(readonly=True)
    expected_hours = fields.Float(string='Hours Expected', readonly=True, aggregator='sum')

    def action_open_attendances(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.employee_id.name,
            'res_model': 'hr.attendance',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.employee_id.id)],
            'context': {'default_employee_id': self.employee_id.id},
        }
