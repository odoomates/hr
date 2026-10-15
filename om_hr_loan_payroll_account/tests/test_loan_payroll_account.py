from datetime import date

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestLoanPayrollAccount(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [Command.link(cls.env.ref('om_hr_payroll.group_hr_payroll_manager').id),
                                  Command.link(cls.env.ref('hr.group_hr_manager').id)]
        clearing = cls.env['account.account'].create({
            'name': 'Gross Salaries', 'code': 'LOANGROSS', 'account_type': 'liability_current'})
        payable = cls.env['account.account'].create({
            'name': 'Salaries to Pay', 'code': 'LOANSALPAY', 'account_type': 'liability_payable', 'reconcile': True})
        basic = cls.env['hr.salary.rule'].create({
            'name': 'Basic', 'code': 'BASIC', 'sequence': 1, 'category_id': cls.env.ref('om_hr_payroll.BASIC').id,
            'amount_select': 'code', 'amount_python_compute': 'result = contract.wage',
            'account_debit': cls.company_data['default_account_expense'].id, 'account_credit': clearing.id})
        net = cls.env.ref('om_hr_payroll.hr_rule_net')
        net.write({'account_debit': clearing.id, 'account_credit': payable.id})
        cls.loan_rule = cls.env.ref('om_hr_loan_payroll.hr_rule_loan')
        cls.loan_rule.write({'account_debit': False, 'account_credit': False})
        structure = cls.env['hr.payroll.structure'].create({
            'name': 'Loan Accounting Structure', 'code': 'LOANACC', 'parent_id': False,
            'rule_ids': [Command.set((basic | cls.loan_rule | net).ids)], 'company_id': cls.env.company.id})
        cls.loan_account = cls.env['account.account'].create({
            'name': 'Employee Loans', 'code': 'EMPLOANP', 'account_type': 'asset_receivable', 'reconcile': True})
        cls.loan_type = cls.env['om.hr.loan.type'].create({'name': 'Payroll Loan', 'single_running': False})
        cls.loan_type.write({'account_id': cls.loan_account.id,
                             'journal_id': cls.company_data['default_journal_bank'].id})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Repaying Employee', 'company_id': cls.env.company.id, 'tz': 'UTC',
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1), 'wage': 3000.0,
            'struct_id': structure.id})

    def test_rule_accounts_set_from_the_loan_type(self):
        self.assertEqual(self.loan_rule.account_debit, self.loan_account)
        self.assertEqual(self.loan_rule.account_credit, self.env.ref('om_hr_payroll.hr_rule_net').account_debit)

    def test_installment_deducted_repays_the_loan_account(self):
        loan = self.env['om.hr.loan'].create({
            'employee_id': self.employee.id, 'type_id': self.loan_type.id, 'amount': 600.0,
            'installment_count': 2, 'date': date(2026, 6, 1), 'date_start': date(2026, 8, 1)})
        loan._compute_installments()
        loan.write({'state': 'approved', 'approval_state': 'approved'})
        loan.action_disburse()

        with Form(self.env['hr.payslip']) as form:
            form.employee_id = self.employee
            form.date_from = date(2026, 8, 1)
            form.date_to = date(2026, 8, 31)
            form.journal_id = self.company_data['default_journal_misc']
        payslip = form.record
        payslip.compute_sheet()
        payslip.action_payslip_done()

        loan_line = payslip.move_id.line_ids.filtered(lambda line: line.account_id == self.loan_account)
        self.assertEqual((loan_line.credit, loan_line.partner_id), (300.0, self.employee.work_contact_id))
        self.assertTrue(loan_line.matched_debit_ids, 'matched with the loan paid out')
        owed = self.env['account.move.line'].search([
            ('account_id', '=', self.loan_account.id), ('partner_id', '=', self.employee.work_contact_id.id),
            ('parent_state', '=', 'posted')])
        self.assertEqual(sum(owed.mapped('balance')), 300.0)
        self.assertEqual(loan.line_ids[0].state, 'paid')

    def test_each_loan_type_repays_its_own_account(self):
        """ Two loan types on two loan accounts: each installment repays the account of its loan. """
        advance_account = self.env['account.account'].create({
            'name': 'Salary Advances', 'code': 'EMPADVP', 'account_type': 'asset_receivable', 'reconcile': True})
        advance_type = self.env['om.hr.loan.type'].create({'name': 'Payroll Advance', 'single_running': False})
        advance_type.write({'account_id': advance_account.id,
                            'journal_id': self.company_data['default_journal_bank'].id})
        self.assertEqual(self.loan_rule.account_debit, self.loan_account, 'the rule keeps the first account')
        loans = self.env['om.hr.loan']
        for loan_type, amount, count in ((self.loan_type, 600.0, 2), (advance_type, 100.0, 1)):
            loan = self.env['om.hr.loan'].create({
                'employee_id': self.employee.id, 'type_id': loan_type.id, 'amount': amount,
                'installment_count': count, 'date': date(2026, 6, 1), 'date_start': date(2026, 8, 1)})
            loan._compute_installments()
            loan.write({'state': 'approved', 'approval_state': 'approved'})
            loan.action_disburse()
            loans |= loan
        with Form(self.env['hr.payslip']) as form:
            form.employee_id = self.employee
            form.date_from = date(2026, 8, 1)
            form.date_to = date(2026, 8, 31)
            form.journal_id = self.company_data['default_journal_misc']
        payslip = form.record
        payslip.compute_sheet()
        payslip.action_payslip_done()
        move_lines = payslip.move_id.line_ids
        loan_line = move_lines.filtered(lambda line: line.account_id == self.loan_account)
        advance_line = move_lines.filtered(lambda line: line.account_id == advance_account)
        self.assertEqual((loan_line.credit, advance_line.credit), (300.0, 100.0))
        self.assertEqual((advance_line.partner_id, advance_line.reconciled), (self.employee.work_contact_id, True),
                         'the advance is fully repaid and matched')
        self.assertTrue(loan_line.matched_debit_ids)
        self.assertAlmostEqual(sum(move_lines.mapped('balance')), 0.0)
        self.assertEqual(loans.mapped('state'), ['running', 'paid'])
