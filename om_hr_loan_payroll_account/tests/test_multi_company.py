from datetime import date

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestLoanPayrollAccountMultiCompany(AccountTestInvoicingCommon):
    """ The loan rule and a loan type shared by two companies: the installments of a payslip of company B repay
        the loan account of company B, never the one of company A. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [Command.link(cls.env.ref('om_hr_payroll.group_hr_payroll_manager').id),
                                  Command.link(cls.env.ref('hr.group_hr_manager').id)]
        cls.company_b_data = cls.setup_other_company(name='Loan Payroll B')
        cls.company_b = cls.company_b_data['company']
        cls.env.user.company_ids = [Command.link(cls.company_b.id)]
        cls.loan_type = cls.env['hr.loan.type'].create({
            'name': 'Shared Payroll Loan', 'single_running': False, 'company_id': False})
        cls.accounts = {}
        for data in (cls.company_data, cls.company_b_data):
            company = data['company']
            Account = cls.env['account.account'].with_company(company)
            clearing = Account.create({'name': 'Gross', 'code': 'LPGROSS', 'account_type': 'liability_current'})
            payable = Account.create({'name': 'To Pay', 'code': 'LPPAY', 'account_type': 'liability_payable',
                                      'reconcile': True})
            loans = Account.create({'name': 'Loans', 'code': 'LPLOAN', 'account_type': 'asset_receivable',
                                    'reconcile': True})
            cls.accounts[company] = loans
            cls.env.ref('om_hr_payroll.hr_rule_basic').with_company(company).write({
                'account_debit': data['default_account_expense'].id, 'account_credit': clearing.id})
            cls.env.ref('om_hr_payroll.hr_rule_net').with_company(company).write({
                'account_debit': clearing.id, 'account_credit': payable.id})
            cls.env.ref('om_hr_loan_payroll.hr_rule_loan').with_company(company).write({
                'account_debit': False, 'account_credit': False})
            cls.loan_type.with_company(company).write({
                'account_id': loans.id, 'journal_id': data['default_journal_bank'].id})
        rules = cls.env.ref('om_hr_payroll.hr_rule_basic') | cls.env.ref('om_hr_loan_payroll.hr_rule_loan') \
            | cls.env.ref('om_hr_payroll.hr_rule_net')
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Shared Loan Accounting', 'code': 'LPMC', 'parent_id': False, 'company_id': False,
            'rule_ids': [Command.set(rules.ids)]})

    def test_installment_repays_the_loan_account_of_the_payslip_company(self):
        company = self.company_b
        employee = self.env['hr.employee'].with_company(company).create({
            'name': 'Repaying of B', 'company_id': company.id, 'tz': 'UTC', 'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1), 'wage': 3000.0, 'struct_id': self.structure.id})
        loan = self.env['hr.loan'].with_company(company).create({
            'employee_id': employee.id, 'type_id': self.loan_type.id, 'amount': 600.0, 'installment_count': 2,
            'date': date(2026, 6, 1), 'date_start': date(2026, 8, 1)})
        loan._compute_installments()
        loan.write({'state': 'approved', 'approval_state': 'approved'})
        loan.action_disburse()
        with Form(self.env['hr.payslip'].with_company(company)) as form:
            form.employee_id = employee
            form.date_from = date(2026, 8, 1)
            form.date_to = date(2026, 8, 31)
        payslip = form.record
        payslip.compute_sheet()
        payslip.action_payslip_done()
        self.assertEqual(payslip.move_id.company_id, company)
        accounts = payslip.move_id.line_ids.account_id
        self.assertIn(self.accounts[company], accounts)
        self.assertNotIn(self.accounts[self.env.company], accounts)
        repaid = payslip.move_id.line_ids.filtered(lambda line: line.account_id == self.accounts[company])
        self.assertEqual((repaid.credit, repaid.partner_id), (300.0, employee.work_contact_id))
