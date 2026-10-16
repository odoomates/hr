from odoo import _, fields, models


class OmHrLatenessPenaltyWizard(models.TransientModel):
    _name = 'om.hr.lateness.penalty.wizard'
    _description = 'Compute Lateness Penalties'

    month = fields.Date(required=True, default=lambda self: fields.Date.subtract(
        fields.Date.context_today(self).replace(day=1), months=1))
    employee_ids = fields.Many2many('hr.employee', string='Employees', help='Leave empty for all the employees.')

    def action_compute(self):
        self.ensure_one()
        self.env['om.hr.payroll.adjustment']._check_payroll()
        employees = self.employee_ids or self.env['hr.employee'].search([('company_id', 'in', self.env.companies.ids)])
        adjustments = self.env['om.hr.lateness']._om_compute_penalties(self.month, employees)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lateness Penalties'),
            'res_model': 'om.hr.payroll.adjustment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', adjustments.ids)],
        }
