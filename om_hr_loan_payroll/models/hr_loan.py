from odoo import fields, models


class OmHrLoanLine(models.Model):
    _inherit = 'om.hr.loan.line'

    payslip_id = fields.Many2one('hr.payslip', string='Payslip', ondelete='set null', index=True, copy=False,
                                 help='The payslip deducting the installment.')
