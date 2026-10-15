from odoo import models


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    def _get_partner_id(self, credit_account):
        """ What the employee repays of a loan is matched with their loan: the employee is the partner of the
            lines on a loan account. """
        account = self.salary_rule_id.account_credit if credit_account else self.salary_rule_id.account_debit
        if account and account in self.env['om.hr.loan.type'].sudo()._om_loan_accounts(self.slip_id.company_id):
            return self.slip_id.employee_id.sudo().work_contact_id.id
        return super()._get_partner_id(credit_account)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _prepare_payslip_move_lines(self, date):
        """ The salary rule of the loans holds one loan account: the installments of the loans of a type with another
            loan account repay that account instead, on journal items of their own. """
        values = super()._prepare_payslip_move_lines(date)
        rule = self.env.ref('om_hr_loan_payroll.hr_rule_loan', raise_if_not_found=False)
        slip = self.with_company(self.company_id)
        rule_account = rule and rule.sudo().with_company(slip.company_id).account_debit
        loan_lines = slip._om_hr_loan_lines()
        payslip_line = slip.line_ids.filtered(lambda line: line.salary_rule_id == rule)[:1]
        if not rule_account or not loan_lines or not payslip_line:
            return values
        currency = slip.company_id.currency_id
        by_account = {}
        for loan_line in loan_lines:
            account = loan_line.loan_id.type_id.sudo().with_company(slip.company_id).account_id or rule_account
            by_account[account] = by_account.get(account, 0.0) + loan_line.amount
        if set(by_account) == {rule_account}:
            return values
        partner = slip.employee_id.sudo().work_contact_id
        result = []
        for vals in values:
            if vals['account_id'] != rule_account.id or vals['name'] != payslip_line.name:
                result.append(vals)
                continue
            # the item of the rule, split by loan account; the last takes what the rounding leaves
            total = vals['credit'] - vals['debit']
            installments = sum(by_account.values())
            left = total
            accounts = list(by_account.items())
            for index, (account, amount) in enumerate(accounts):
                part = left if index == len(accounts) - 1 else currency.round(total * amount / installments)
                left -= part
                result.append(dict(vals, account_id=account.id, partner_id=partner.id or vals['partner_id'],
                                   debit=-part if part < 0 else 0.0, credit=part if part > 0 else 0.0))
        return result

    def action_payslip_done(self):
        result = super().action_payslip_done()
        self._om_reconcile_loans()
        return result

    def _om_reconcile_loans(self):
        self.filtered(lambda slip: slip.move_id.state == 'posted')._om_hr_loan_lines().loan_id._om_reconcile()


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def done_payslip_run(self):
        result = super().done_payslip_run()
        self.slip_ids._om_reconcile_loans()
        return result
