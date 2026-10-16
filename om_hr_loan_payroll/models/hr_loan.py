from odoo import fields, models


class HrLoanLine(models.Model):
    _inherit = 'hr.loan.line'

    payslip_id = fields.Many2one('hr.payslip', ondelete='set null', index=True, copy=False,
                                 help='The payslip deducting the installment.', check_company=True)
