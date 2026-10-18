from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    om_payroll_worked_days_source = fields.Selection([
        ('work_entries', 'Work Entries'),
        ('schedule', 'Working Schedule'),
    ], string='Worked Days From', default='work_entries', required=True,
        help='Work Entries: the work entries of the employees, i.e. the working schedule less the time off, or the '
             'validated attendances for the contracts based on attendances. Working Schedule: the working schedule '
             'and the time off only, as before version 2.2.0.')
    om_payroll_month_days = fields.Float(
        string='Days per Month', default=30.0,
        help='The daily wage is the monthly wage divided by these days, e.g. 30, or 21.67 working days. It pays the '
             'unused time off, the overtime, and the rules reading daily_wage or hourly_wage.')
    om_payroll_variance_threshold = fields.Float(
        string='Variance Threshold (%)', default=10.0,
        help='Mark as Done of a payslip batch first lists the payslips whose gross or net pay changes by more than '
             'this percentage from the last confirmed payslip of the employee, and the employees without one. '
             '0 turns the check off.')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_om_hr_payroll_account = fields.Boolean(string='Payroll Accounting')
    om_payroll_worked_days_source = fields.Selection(related='company_id.om_payroll_worked_days_source',
                                                     readonly=False)
    om_payroll_month_days = fields.Float(related='company_id.om_payroll_month_days', readonly=False)
    om_payroll_variance_threshold = fields.Float(related='company_id.om_payroll_variance_threshold', readonly=False)
