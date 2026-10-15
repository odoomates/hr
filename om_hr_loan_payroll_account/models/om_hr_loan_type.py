from odoo import api, models


class OmHrLoanType(models.Model):
    _inherit = 'om.hr.loan.type'

    @api.model
    def _om_loan_accounts(self, company):
        """ :return: the loan accounts of the loan types in the company """
        return self.with_company(company).with_context(active_test=False).search([]).account_id

    @api.model_create_multi
    def create(self, vals_list):
        types = super().create(vals_list)
        types._om_set_loan_rule_accounts()
        return types

    def write(self, vals):
        result = super().write(vals)
        if 'account_id' in vals:
            self._om_set_loan_rule_accounts()
        return result

    def _om_set_loan_rule_accounts(self):
        """ The loan installments of the payslips repay the loan account: the deduction is negative, so the loan
            account is the debit account of the loan rule, credited by it. Its other side is the account the net
            salary is taken from. Accounts already set on the rule are kept. """
        rule = self.env.ref('om_hr_loan_payroll.hr_rule_loan', raise_if_not_found=False)
        account = self.filtered('account_id')[:1].account_id
        if not rule or not account:
            return
        rule = rule.sudo()
        values = {}
        if not rule.account_debit:
            values['account_debit'] = account.id
        if not rule.account_credit:
            net = self.env.ref('om_hr_payroll.hr_rule_net', raise_if_not_found=False)
            if net and net.sudo().account_debit:
                values['account_credit'] = net.sudo().account_debit.id
        if values:
            rule.write(values)
