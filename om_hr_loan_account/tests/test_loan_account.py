from datetime import date

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestLoanAccount(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [Command.link(cls.env.ref('hr.group_hr_manager').id)]
        cls.loan_account = cls.env['account.account'].create({
            'name': 'Employee Loans', 'code': 'EMPLOAN', 'account_type': 'asset_receivable', 'reconcile': True})
        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.loan_type = cls.env['hr.loan.type'].create({'name': 'Accounted Loan', 'single_running': False})
        cls.loan_type.write({'account_id': cls.loan_account.id, 'journal_id': cls.bank_journal.id})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Borrowing Employee', 'company_id': cls.env.company.id,
            'date_version': date(2024, 1, 1), 'contract_date_start': date(2024, 1, 1), 'wage': 3000.0})
        cls.partner = cls.employee.work_contact_id

    def running_loan(self, loan_type=None):
        loan = self.env['hr.loan'].create({
            'employee_id': self.employee.id, 'type_id': (loan_type or self.loan_type).id, 'amount': 900.0,
            'installment_count': 3, 'date': date(2026, 6, 1), 'date_start': date(2026, 7, 1)})
        loan._compute_installments()
        loan.write({'state': 'approved', 'approval_state': 'approved'})
        loan.action_disburse()
        return loan

    def balance(self):
        lines = self.env['account.move.line'].search([
            ('account_id', '=', self.loan_account.id), ('partner_id', '=', self.partner.id),
            ('parent_state', '=', 'posted')])
        return sum(lines.mapped('balance')), lines

    def test_paid_out_and_repaid(self):
        loan = self.running_loan()
        payout = loan.payment_ids
        self.assertEqual((payout.payment_type, payout.amount), ('outbound', 900.0))
        self.assertIn(payout.state, ('in_process', 'paid'), 'posted')
        self.assertEqual(payout.destination_account_id, self.loan_account)
        self.assertEqual(payout.partner_id, self.partner)
        self.assertEqual(self.balance()[0], 900.0, 'the employee owes the loan')

        loan.line_ids[0].action_mark_paid()
        repayment = loan.payment_ids - payout
        self.assertEqual((repayment.payment_type, repayment.amount), ('inbound', 300.0))
        self.assertEqual(self.balance()[0], 600.0)

        loan.action_settle()
        self.assertEqual(loan.state, 'paid')
        self.assertEqual(len(loan.payment_ids), 3)
        total, lines = self.balance()
        self.assertEqual(total, 0.0)
        self.assertTrue(all(lines.mapped('reconciled')), 'the loan account is reconciled for the employee')

    def test_loan_type_without_accounting(self):
        plain = self.env['hr.loan.type'].create({'name': 'Plain Loan', 'single_running': False})
        loan = self.running_loan(plain)
        self.assertEqual(loan.state, 'running')
        self.assertFalse(loan.payment_ids)
