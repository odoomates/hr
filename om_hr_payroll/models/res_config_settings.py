from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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
    om_payroll_keep_lines_on_confirm = fields.Boolean(
        string='Confirm the Lines as They Are',
        help='Confirming a computed payslip keeps its lines as they are, the ones edited by hand included, instead '
             'of computing the payslip again. The lines are not added up again: a line edited by hand leaves the '
             'other lines, e.g. the net salary, to edit too.')
    om_payroll_monthly_batch = fields.Boolean(
        string='Monthly Batch',
        help='Each month, from the day set, a payslip batch of the month is created with the payslips of the '
             'employees under contract, in draft, to check and confirm.')
    om_payroll_monthly_batch_day = fields.Integer(
        string='Monthly Batch Day', default=25,
        help='The day of the month the batch is created on, or the last day of a shorter month.')

    @api.constrains('om_payroll_monthly_batch_day')
    def _check_om_payroll_monthly_batch_day(self):
        if any(not 1 <= company.om_payroll_monthly_batch_day <= 31 for company in self):
            raise ValidationError(_('The day of the monthly batch is a day of the month, from 1 to 31.'))


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_om_hr_payroll_account = fields.Boolean(string='Payroll Accounting')
    om_payroll_worked_days_source = fields.Selection(related='company_id.om_payroll_worked_days_source',
                                                     readonly=False)
    om_payroll_month_days = fields.Float(related='company_id.om_payroll_month_days', readonly=False)
    om_payroll_variance_threshold = fields.Float(related='company_id.om_payroll_variance_threshold', readonly=False)
    om_payroll_keep_lines_on_confirm = fields.Boolean(related='company_id.om_payroll_keep_lines_on_confirm',
                                                      readonly=False)
    om_payroll_monthly_batch = fields.Boolean(related='company_id.om_payroll_monthly_batch', readonly=False)
    om_payroll_monthly_batch_day = fields.Integer(related='company_id.om_payroll_monthly_batch_day', readonly=False)
