from odoo import fields, models


class HrLoanType(models.Model):
    _inherit = 'hr.loan.type'

    account_id = fields.Many2one(
        'account.account', string='Loan Account', company_dependent=True,
        domain="[('account_type', '=', 'asset_receivable'), ('active', '=', True)]",
        help='What the employees owe for the loans of this type: debited when a loan is paid out, credited as it '
             'is repaid. A receivable account, reconciled per employee.')
    journal_id = fields.Many2one(
        'account.journal', string='Payment Journal', company_dependent=True,
        domain="[('type', 'in', ('bank', 'cash'))]", check_company=True,
        help='The bank or cash journal paying the loans out, and receiving what is repaid outside the payroll.')
