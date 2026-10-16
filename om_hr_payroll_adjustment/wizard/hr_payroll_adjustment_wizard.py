from odoo import api, fields, models
from odoo.exceptions import UserError


class HrPayrollAdjustmentWizard(models.TransientModel):
    """ The same adjustment for many employees at once, e.g. a bonus for a department. """
    _name = 'hr.payroll.adjustment.wizard'
    _description = 'Add Payroll Adjustments'

    department_id = fields.Many2one('hr.department', help='Adds the employees of the department.')
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    type_id = fields.Many2one('hr.payroll.adjustment.type', required=True)
    kind = fields.Selection(related='type_id.kind')
    description = fields.Char()
    recurrence = fields.Selection([
        ('once', 'Once'),
        ('months', 'Monthly, for a number of months'),
        ('total', 'Monthly, until a total'),
    ], required=True, default='once')
    amount_type = fields.Selection([('fixed', 'Fixed Amount'), ('percent', 'Percentage')],
                                   required=True, default='fixed')
    amount = fields.Monetary(string='Amount per Month')
    percent = fields.Float(string='Percentage', digits=(16, 2))
    percent_base = fields.Selection([('wage', 'of the Wage'), ('gross', 'of the Gross')], string='Base',
                                    default='wage')
    month_count = fields.Integer(string='Months', default=1)
    total_amount = fields.Monetary(string='Total')
    date_start = fields.Date(string='First Month', required=True,
                             default=lambda self: fields.Date.context_today(self).replace(day=1))
    confirm = fields.Boolean(string='Confirm Now', default=True,
                             help='Run them, or send them for approval when their type asks for it, right away.')

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.department_id:
            self.employee_ids |= self.env['hr.employee'].search([('department_id', 'child_of', self.department_id.id)])

    def action_create(self):
        self.ensure_one()
        if not self.employee_ids:
            raise UserError(self.env._('Choose the employees.'))
        adjustments = self.env['hr.payroll.adjustment'].create([{
            'employee_id': employee.id,
            'type_id': self.type_id.id,
            'description': self.description,
            'recurrence': self.recurrence,
            'amount_type': self.amount_type,
            'amount': self.amount,
            'percent': self.percent,
            'percent_base': self.percent_base,
            'month_count': self.month_count if self.recurrence == 'months' else 1,
            'total_amount': self.total_amount,
            'date_start': self.date_start,
        } for employee in self.employee_ids])
        if self.confirm:
            adjustments.action_confirm()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Payroll Adjustments'),
            'res_model': 'hr.payroll.adjustment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', adjustments.ids)],
        }
