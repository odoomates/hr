from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestLoanAccountMultiCompany(AccountTestInvoicingCommon):
    """ A loan type shared by two companies: each company pays its loans out with its own account and journal. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [Command.link(cls.env.ref('hr.group_hr_manager').id)]
        cls.company_b_data = cls.setup_other_company(name='Loans Accounting B')
        cls.company_b = cls.company_b_data['company']
        cls.env.user.company_ids = [Command.link(cls.company_b.id)]
        cls.loan_type = cls.env['hr.loan.type'].create({
            'name': 'Shared Accounted Loan', 'single_running': False, 'company_id': False})
        cls.account_a = cls.env['account.account'].create({
            'name': 'Employee Loans A', 'code': 'LOANMCA', 'account_type': 'asset_receivable', 'reconcile': True})
        cls.account_b = cls.env['account.account'].with_company(cls.company_b).create({
            'name': 'Employee Loans B', 'code': 'LOANMCB', 'account_type': 'asset_receivable', 'reconcile': True})
        cls.loan_type.write({'account_id': cls.account_a.id, 'journal_id': cls.company_data['default_journal_bank'].id})
        cls.loan_type.with_company(cls.company_b).write({
            'account_id': cls.account_b.id, 'journal_id': cls.company_b_data['default_journal_bank'].id})
        cls.employee_b = cls.env['hr.employee'].with_company(cls.company_b).create({
            'name': 'Borrower of B', 'company_id': cls.company_b.id,
            'date_version': date(2024, 1, 1), 'contract_date_start': date(2024, 1, 1), 'wage': 3000.0})

    def test_paid_out_with_the_account_and_journal_of_its_company(self):
        loan = self.env['hr.loan'].with_company(self.company_b).create({
            'employee_id': self.employee_b.id, 'type_id': self.loan_type.id, 'amount': 900.0,
            'installment_count': 3, 'date': date(2026, 6, 1), 'date_start': date(2026, 7, 1)})
        loan._compute_installments()
        loan.write({'state': 'approved', 'approval_state': 'approved'})
        loan.action_disburse()
        payment = loan.payment_ids
        self.assertEqual((payment.company_id, payment.journal_id), (self.company_b,
                                                                     self.company_b_data['default_journal_bank']))
        self.assertIn(self.account_b, payment.move_id.line_ids.account_id)
        self.assertNotIn(self.account_a, payment.move_id.line_ids.account_id)

    def test_no_journal_of_another_company(self):
        with self.assertRaises(UserError):
            self.loan_type.with_company(self.company_b).journal_id = self.company_data['default_journal_bank']

    def test_no_payment_of_another_company(self):
        loan = self.env['hr.loan'].with_company(self.company_b).create({
            'employee_id': self.employee_b.id, 'type_id': self.loan_type.id, 'amount': 300.0,
            'installment_count': 1, 'date': date(2026, 6, 1), 'date_start': date(2026, 7, 1)})
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound', 'partner_type': 'customer', 'amount': 10.0,
            'journal_id': self.company_data['default_journal_bank'].id})
        with self.assertRaises(UserError):
            payment.loan_id = loan
