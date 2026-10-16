from datetime import date

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestLoanMultiCompany(TransactionCase):
    """ A loan stays in the company of its employee, with the loan types of that company or shared ones. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Loan Company B'})
        cls.hr_user = new_test_user(cls.env, 'om_loan_mc_hr', groups='base.group_user,hr.group_hr_user',
                                    company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        Employee = cls.env['hr.employee']
        cls.employee_a = Employee.create({'name': 'Loan Employee A'})
        cls.employee_b = Employee.with_company(cls.company_b).create({'name': 'Loan Employee B',
                                                                       'company_id': cls.company_b.id})
        Type = cls.env['hr.loan.type']
        cls.type_b = Type.create({'name': 'Loan Type B', 'company_id': cls.company_b.id})
        cls.shared_type = Type.create({'name': 'Shared Loan Type'})

    def loan(self, employee, loan_type):
        return self.env['hr.loan'].create({
            'employee_id': employee.id, 'type_id': loan_type.id, 'amount': 1000.0, 'installment_count': 2,
            'date': date(2026, 7, 10), 'date_start': date(2026, 8, 15)})

    def test_other_company_hidden(self):
        loan_a, loan_b = self.loan(self.employee_a, self.shared_type), self.loan(self.employee_b, self.shared_type)
        self.assertEqual((loan_a.company_id, loan_b.company_id), (self.company_a, self.company_b))
        Loan = self.env['hr.loan'].with_user(self.hr_user)
        self.assertEqual(Loan.search([('id', 'in', (loan_a | loan_b).ids)]), loan_a)
        with self.assertRaises(AccessError):
            loan_b.with_user(self.hr_user).read(['amount'])
        self.assertNotIn(self.type_b, self.env['hr.loan.type'].with_user(self.hr_user).search([]))

    def test_no_link_across_companies(self):
        with self.assertRaises(UserError):
            self.loan(self.employee_a, self.type_b)

    def test_shared_type(self):
        self.assertTrue(self.loan(self.employee_a, self.shared_type))
        self.assertTrue(self.loan(self.employee_b, self.shared_type))
        self.assertIn(self.shared_type, self.env['hr.loan.type'].with_user(self.hr_user).search([]))
