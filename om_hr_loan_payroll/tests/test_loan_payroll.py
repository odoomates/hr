from datetime import date

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestLoanPayroll(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loan_rule = cls.env.ref('om_hr_loan_payroll.hr_rule_loan')
        basic = cls.env['hr.salary.rule'].create({
            'name': 'Basic', 'code': 'BASIC', 'sequence': 1, 'category_id': cls.env.ref('om_hr_payroll.BASIC').id,
            'amount_select': 'code', 'amount_python_compute': 'result = contract.wage'})
        net = cls.env.ref('om_hr_payroll.hr_rule_net')
        rules = basic | cls.loan_rule | net
        if 'account_debit' in rules._fields:
            # payroll accounting is installed: a confirmed payslip is posted, so the rules need accounts
            cls.env['account.journal'].create({'name': 'Payroll Loan', 'code': 'PAYLN', 'type': 'general'})
            (basic | cls.loan_rule).write({
                'account_debit': cls.env['account.account'].create({
                    'name': 'Payroll Expense Loan', 'code': 'PAYEXPLN', 'account_type': 'expense'}).id,
                'account_credit': cls.env['account.account'].create({
                    'name': 'Payroll Payable Loan', 'code': 'PAYPAYLN', 'account_type': 'liability_current'}).id,
            })
            net.write({'account_debit': False, 'account_credit': False})
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Loan Structure', 'code': 'LOANS', 'rule_ids': [Command.set(rules.ids)]})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Borrower', 'tz': 'UTC', 'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1), 'wage': 3000.0, 'struct_id': cls.structure.id})
        loan_type = cls.env['hr.loan.type'].create({'name': 'Payroll Loan', 'single_running': False})
        cls.loan = cls.env['hr.loan'].create({
            'employee_id': cls.employee.id, 'type_id': loan_type.id, 'amount': 900.0, 'installment_count': 3,
            'date': date(2026, 7, 1), 'date_start': date(2026, 8, 1)})
        cls.loan._compute_installments()
        cls.loan.write({'state': 'running', 'approval_state': 'approved'})

    def payslip(self, month):
        with Form(self.env['hr.payslip']) as form:
            form.employee_id = self.employee
            form.date_from = date(2026, month, 1)
            form.date_to = date(2026, month, 28)
        payslip = form.record
        payslip.compute_sheet()
        return payslip

    @staticmethod
    def total(payslip, code):
        return sum(payslip.line_ids.filtered(lambda line: line.code == code).mapped('total'))

    def test_base_structure_deducts_loans(self):
        self.assertIn(self.loan_rule, self.env.ref('om_hr_payroll.structure_base').rule_ids)

    def test_deducted_and_repaid(self):
        august = self.payslip(8)
        self.assertEqual(self.total(august, 'LOAN'), -300)
        self.assertEqual(self.total(august, 'NET'), 2700)
        self.assertEqual(self.loan.line_ids[0].payslip_id, august)
        august.action_payslip_done()
        self.assertEqual(self.loan.line_ids[0].state, 'paid')
        self.assertEqual(self.loan.amount_residual, 600)

        # a draft payslip of the same month does not take the installment again
        self.assertEqual(self.total(self.payslip(8), 'LOAN'), 0)

        for month in (9, 10):
            self.payslip(month).action_payslip_done()
        self.assertEqual(self.loan.state, 'paid')

    def test_missed_month(self):
        """ No payslip in August: September deducts both installments. """
        self.assertEqual(self.total(self.payslip(9), 'LOAN'), -600)

    def test_no_installment_before_the_first(self):
        july = self.payslip(7)
        self.assertEqual(self.total(july, 'LOAN'), 0)
        self.assertFalse(july.line_ids.filtered(lambda line: line.code == 'LOAN'))

    def test_cancel_and_refund(self):
        august = self.payslip(8)
        august.action_payslip_cancel()
        self.assertFalse(self.loan.line_ids[0].payslip_id)

        august = self.payslip(8)
        august.action_payslip_done()
        self.assertEqual(self.loan.line_ids[0].state, 'paid')
        august.refund_sheet()
        self.assertEqual(self.loan.line_ids[0].state, 'to_pay', 'the refunded payslip gives the installment back')
        self.assertEqual(self.total(self.payslip(8), 'LOAN'), -300)

    def test_back_to_draft(self):
        for month in (8, 9):
            self.payslip(month).action_payslip_done()
        october = self.payslip(10)
        october.action_payslip_done()
        self.assertEqual(self.loan.state, 'paid')
        october.action_payslip_draft()
        self.assertEqual(self.loan.state, 'running')
        self.assertEqual(self.loan.line_ids[2].payslip_id, october, 'kept to deduct it when confirmed again')
        october.action_payslip_done()
        self.assertEqual(self.loan.state, 'paid')
