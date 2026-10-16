from datetime import timedelta

from odoo import api, fields, models
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
        self.env['hr.shift']._check_planner()
        employees = self.env['hr.employee'].sudo().browse(self.employee_ids.ids)
        if self.mode == 'start':
            employees._start_rostering(self.date)
        else:
            if not self.calendar_id:
                raise UserError(self.env._('Choose the working schedule of the employees from then on.'))
            employees._stop_rostering(self.date, self.calendar_id)
        return {'type': 'ir.actions.act_window_close'}


class HrShiftRotationWizard(models.TransientModel):
    """ A rotation laid over some days for some employees, each starting further in the cycle when staggered. """
    _name = 'hr.shift.rotation.wizard'
    _description = 'Apply a Shift Rotation'

    rotation_id = fields.Many2one('hr.shift.rotation', required=True)
    employee_ids = fields.Many2many('hr.employee.public', string='Employees', required=True)
    date_from = fields.Date(string='From', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='To', required=True,
                          default=lambda self: fields.Date.context_today(self) + timedelta(days=27))
    stagger = fields.Boolean(default=True,
                             help='Each employee starts one day further in the cycle, so that they do not all work '
                                  'the same shift on the same day.')
    skip_existing = fields.Boolean(string='Keep Existing Shifts', default=True,
                                   help='The days an employee has a shift already are left as they are.')

    def action_apply(self):
        self.ensure_one()
        self.env['hr.shift']._check_planner()
        if self.date_to < self.date_from:
            raise UserError(self.env._('The rotation ends after it starts.'))
        lines = self.rotation_id.line_ids
        Shift = self.env['hr.shift']
        existing = {(shift.employee_id.id, shift.date) for shift in Shift.search([
            ('employee_id', 'in', self.employee_ids.ids), ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)])}
        values = []
        for index, employee in enumerate(self.employee_ids):
            offset = index if self.stagger else 0
            day = self.date_from
            while day <= self.date_to:
                line = lines[((day - self.date_from).days + offset) % len(lines)]
                if line.template_id and not (self.skip_existing and (employee.id, day) in existing):
                    values.append(dict(line.template_id._shift_values(), employee_id=employee.id, date=day))
                day += timedelta(days=1)
        shifts = Shift.create(values)
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Shifts'),
            'res_model': 'hr.shift',
            'view_mode': 'list,form',
            'domain': [('id', 'in', shifts.ids)],
        }


class HrShiftPublishWizard(models.TransientModel):
    _name = 'hr.shift.publish.wizard'
    _description = 'Publish Shifts Despite Warnings'

    shift_ids = fields.Many2many('hr.shift', string='Shifts', required=True)
    warnings = fields.Text(compute='_compute_warnings')
    reason = fields.Char(help='Kept on each shift published despite a warning.')

    @api.depends('shift_ids')
    def _compute_warnings(self):
        for wizard in self:
            warnings = wizard.shift_ids._check()
            wizard.warnings = '\n'.join('%s: %s' % (shift.display_name, '; '.join(warnings[shift.id]))
                                        for shift in wizard.shift_ids if warnings.get(shift.id))

    def action_publish(self):
        self.ensure_one()
        return self.shift_ids.with_context(om_shift_override=True,
                                           om_shift_override_reason=self.reason).action_publish()
