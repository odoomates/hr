# -*- coding:utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

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
    om_payroll_monthly_batch = fields.Boolean(related='company_id.om_payroll_monthly_batch', readonly=False)
    om_payroll_monthly_batch_day = fields.Integer(related='company_id.om_payroll_monthly_batch_day', readonly=False)
