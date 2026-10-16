from datetime import date

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestAdjustmentMultiCompany(TransactionCase):
    """ An adjustment stays in the company of its employee, of a type of that company or a shared one. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Adjustment Company B'})
        cls.officer = new_test_user(cls.env, 'om_adj_mc_officer',
                                    groups='base.group_user,om_hr_payroll.group_hr_payroll_user',
                                    company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        Employee = cls.env['hr.employee']
        cls.employee_a = Employee.create({'name': 'Adjusted A'})
        cls.employee_b = Employee.with_company(cls.company_b).create({'name': 'Adjusted B',
                                                                       'company_id': cls.company_b.id})
        Type = cls.env['hr.payroll.adjustment.type']
        allowance = cls.env.ref('om_hr_payroll.ALW')
        cls.type_b = Type.create({'name': 'Bonus B', 'code': 'MC_BONUS_B', 'kind': 'addition',
                                  'category_id': allowance.id, 'company_id': cls.company_b.id})
        cls.shared_type = Type.create({'name': 'Shared Bonus', 'code': 'MC_BONUS', 'kind': 'addition',
                                       'category_id': allowance.id})

    def adjustment(self, employee, adjustment_type):
        return self.env['hr.payroll.adjustment'].create({
            'employee_id': employee.id, 'type_id': adjustment_type.id, 'amount': 100.0,
            'date_start': date(2026, 8, 1)})

    def test_other_company_hidden(self):
        adjustment_a = self.adjustment(self.employee_a, self.shared_type)
        adjustment_b = self.adjustment(self.employee_b, self.shared_type)
        self.assertEqual((adjustment_a.company_id, adjustment_b.company_id), (self.company_a, self.company_b))
        Adjustment = self.env['hr.payroll.adjustment'].with_user(self.officer)
        self.assertEqual(Adjustment.search([('id', 'in', (adjustment_a | adjustment_b).ids)]), adjustment_a)
        with self.assertRaises(AccessError):
            adjustment_b.with_user(self.officer).read(['amount'])
        self.assertNotIn(self.type_b, self.env['hr.payroll.adjustment.type'].with_user(self.officer).search([]))

    def test_no_link_across_companies(self):
        with self.assertRaises(UserError):
            self.adjustment(self.employee_a, self.type_b)

    def test_shared_type(self):
        self.assertTrue(self.adjustment(self.employee_a, self.shared_type))
        self.assertTrue(self.adjustment(self.employee_b, self.shared_type))
        self.assertIn(self.shared_type, self.env['hr.payroll.adjustment.type'].with_user(self.officer).search([]))
