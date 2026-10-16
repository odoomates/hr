from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestLoanPayrollMultiCompany(TransactionCase):
    """ Two companies sharing the loan rule: each payslip deducts the installments of its own company. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env['res.company'].create({'name': 'Loans Company B'})
        if 'journal_id' in cls.env['hr.payslip']._fields:
            cls.env['account.journal'].create({
                'name': 'Salaries B', 'code': 'SALLB', 'type': 'general', 'company_id': cls.company_b.id})
        rules = cls.env.ref('om_hr_payroll.hr_rule_basic') | cls.env.ref('om_hr_loan_payroll.hr_rule_loan') \
            | cls.env.ref('om_hr_payroll.hr_rule_net')
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Shared Loans', 'code': 'LOANMC', 'parent_id': False, 'company_id': False,
            'rule_ids': [Command.set(rules.ids)]})
        cls.loan_type = cls.env['hr.loan.type'].create({
            'name': 'Shared Loan', 'single_running': False, 'company_id': False})
        cls.employee_a = cls.new_employee(cls.env.company, 'Borrower A')
        cls.employee_b = cls.new_employee(cls.company_b, 'Borrower B')
        cls.loan_a = cls.running_loan(cls.employee_a, 900.0)
        cls.loan_b = cls.running_loan(cls.employee_b, 600.0)

    @classmethod
    def new_employee(cls, company, name):
        return cls.env['hr.employee'].with_company(company).create({
            'name': name, 'company_id': company.id, 'tz': 'UTC', 'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1), 'wage': 3000.0, 'struct_id': cls.structure.id})

    @classmethod
    def running_loan(cls, employee, amount):
        loan = cls.env['hr.loan'].with_company(employee.company_id).create({
            'employee_id': employee.id, 'type_id': cls.loan_type.id, 'amount': amount, 'installment_count': 3,
            'date': date(2026, 7, 1), 'date_start': date(2026, 8, 1)})
        loan._compute_installments()
        loan.write({'state': 'running', 'approval_state': 'approved'})
        return loan

    def payslip(self, employee):
        with Form(self.env['hr.payslip'].with_company(employee.company_id)) as form:
            form.employee_id = employee
            form.date_from = date(2026, 8, 1)
            form.date_to = date(2026, 8, 31)
        payslip = form.record
        payslip.compute_sheet()
        return payslip

    @staticmethod
    def total(payslip):
        return sum(payslip.line_ids.filtered(lambda line: line.code == 'LOAN').mapped('total'))

    def test_each_payslip_deducts_the_loans_of_its_company(self):
        payslip_b = self.payslip(self.employee_b)
        self.assertEqual(payslip_b.company_id, self.company_b)
        self.assertEqual(self.total(payslip_b), -200.0)
        self.assertEqual(self.loan_b.line_ids[0].payslip_id, payslip_b)
        self.assertFalse(self.loan_a.line_ids.payslip_id)
        self.assertEqual(self.total(self.payslip(self.employee_a)), -300.0)

    def test_no_installment_on_a_payslip_of_another_company(self):
        payslip_b = self.payslip(self.employee_b)
        with self.assertRaises(UserError):
            self.loan_a.line_ids[0].payslip_id = payslip_b

    def test_installments_of_another_company_are_hidden(self):
        officer = new_test_user(
            self.env, 'om_mc_loan_officer', groups='base.group_user,hr.group_hr_user',
            company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)])
        Line = self.env['hr.loan.line'].with_user(officer)
        self.assertTrue(Line.search([('loan_id', '=', self.loan_a.id)]))
        self.assertFalse(Line.search([('loan_id', '=', self.loan_b.id)]))
