from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrPayslipAnnualStatement(models.TransientModel):
    """ Prints the annual statement of the employees for a payroll year. """
    _name = 'hr.payslip.annual.statement'
    _description = 'Payroll Annual Statement'

    def _default_year(self):
        today = fields.Date.context_today(self)
        return self.env['hr.payslip']._get_year_start(today, self.env.company).year

    def _default_employees(self):
        if self.env.context.get('active_model') == 'hr.employee':
            return self.env['hr.employee'].browse(self.env.context.get('active_ids'))
        return self.env['hr.employee']

    year = fields.Integer(
        required=True, default=_default_year,
        help='The payroll year starting in this year: the calendar year, or e.g. April of this year to March of the '
             'next when the fiscal year of the company starts in April.')
    date_from = fields.Date(string='From', compute='_compute_dates')
    date_to = fields.Date(string='To', compute='_compute_dates')
    employee_ids = fields.Many2many('hr.employee', string='Employees', default=_default_employees)

    @api.depends('year')
    def _compute_dates(self):
        for wizard in self:
            if 1900 < wizard.year < 3000:
                wizard.date_from, wizard.date_to = self.env['hr.payslip']._get_tax_year(
                    wizard.year, self.env.company)
            else:
                wizard.date_from = wizard.date_to = False

    def action_print(self):
        self.ensure_one()
        if not self.employee_ids:
            raise UserError(_('Choose the employees to print the annual statement of.'))
        if not 1900 < self.year < 3000:
            raise UserError(_('Enter the year as four digits, e.g. 2026.'))
        return self.env.ref('om_hr_payroll.action_report_annual_statement').report_action(
            self.employee_ids, data={'year': self.year})
