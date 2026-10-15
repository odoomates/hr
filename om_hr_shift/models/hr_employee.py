from odoo import SUPERUSER_ID, _, fields, models
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    om_roster_calendar_id = fields.Many2one(
        'resource.calendar', string='Roster Schedule', readonly=True, copy=False, groups='hr.group_hr_user',
        help='The variable working schedule of the employee, written by the published shifts.')
    om_roster_date_start = fields.Date(string='Rostered Since', readonly=True, copy=False, groups='hr.group_hr_user')
    om_shift_ids = fields.One2many('om.hr.shift', 'employee_id', string='Shifts')

    def _om_start_rostering(self, date):
        """ From `date`, the employee works the shifts of the roster: a new version of the contract on a working
            schedule of their own, so that the days before keep the schedule they had. """
        for employee in self.sudo():
            if employee.om_roster_calendar_id:
                continue
            version = employee._get_version(date) or employee.version_id
            previous = version.resource_calendar_id or employee.resource_calendar_id or \
                employee.company_id.resource_calendar_id
            calendar = self.env['resource.calendar'].create({
                'name': _('Roster: %s', employee.name),
                'calendar_type': 'variable',
                'company_id': employee.company_id.id,
                'attendance_ids': [],
                'hours_per_week': previous.hours_per_week or 40.0,
                'days_per_week': previous.days_per_week or 5.0,
                'reference_calendar_id': previous.id,
            })
            employee._om_set_schedule_from(date, version, calendar)
            employee.write({'om_roster_calendar_id': calendar.id, 'om_roster_date_start': date})
            employee.message_post(body=_('Rostered from %s: the published shifts are the working schedule.', date),
                                  subtype_xmlid='mail.mt_note')

    def _om_stop_rostering(self, date, calendar):
        """ From `date`, the employee works `calendar` again; the shifts from then on are dropped. """
        for employee in self.sudo():
            if not employee.om_roster_calendar_id:
                raise UserError(_('%s is not rostered.', employee.name))
            employee.om_shift_ids.filtered(lambda shift: shift.date >= date).unlink()
            version = employee._get_version(date) or employee.version_id
            employee._om_set_schedule_from(date, version, calendar)
            employee.write({'om_roster_calendar_id': False, 'om_roster_date_start': False})
            employee.message_post(body=_('No longer rostered from %(date)s: works %(calendar)s.', date=date,
                                         calendar=calendar.name), subtype_xmlid='mail.mt_note')

    def _om_set_schedule_from(self, date, version, calendar):
        """ `calendar` from `date` on: on the version of that day, or on a new version from then. Core writes the
            new version with the rights of the user: the system user, an HR administrator, does it, for the shift
            planners who are not. """
        self.ensure_one()
        if version.date_version == date:
            version.sudo().resource_calendar_id = calendar
        else:
            self.with_user(SUPERUSER_ID).create_version({'date_version': date, 'resource_calendar_id': calendar.id})

    def action_om_open_rostering(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rostering'),
            'res_model': 'om.hr.shift.rostering.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_ids': self.ids,
                        'default_mode': 'stop' if any(e.sudo().om_roster_calendar_id for e in self) else 'start'},
        }
