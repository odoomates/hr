from odoo import fields, models
from odoo.exceptions import UserError


class HrShiftRosteringWizard(models.TransientModel):
    _name = 'hr.shift.rostering.wizard'
    _description = 'Start or Stop Rostering'

    mode = fields.Selection([('start', 'Start Rostering'), ('stop', 'Stop Rostering')], required=True,
                            default='start')
    # public employees: the shift planners may not be HR officers
    employee_ids = fields.Many2many('hr.employee.public', string='Employees', required=True)
    date = fields.Date(string='From', required=True, default=fields.Date.context_today,
                       help='The first day of the new working schedule; the days before keep theirs.')
    calendar_id = fields.Many2one('resource.calendar', string='Working Schedule',
                                  domain="[('calendar_type', '=', 'fixed')]",
                                  help='The schedule the employees work again when no longer rostered.')

    def action_confirm(self):
        self.ensure_one()
        self.env['om.planning.slot']._check_shift_planner()
        employees = self.env['hr.employee'].sudo().browse(self.employee_ids.ids)
        if self.mode == 'start':
            employees._start_rostering(self.date)
        else:
            if not self.calendar_id:
                raise UserError(self.env._('Choose the working schedule of the employees from then on.'))
            employees._stop_rostering(self.date, self.calendar_id)
        return {'type': 'ir.actions.act_window_close'}
