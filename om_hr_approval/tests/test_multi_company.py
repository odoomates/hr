from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestMultiCompany(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Requests Company B'})
        cls.hr_a = new_test_user(cls.env, 'om_mc_request_hr_a', groups='base.group_user,hr.group_hr_user',
                                 company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        Employee = cls.env['hr.employee']
        cls.employee_a = Employee.create({'name': 'Request A', 'company_id': cls.company_a.id})
        cls.employee_b = Employee.create({'name': 'Request B', 'company_id': cls.company_b.id})
        Category = cls.env['hr.request.category']
        cls.category = Category.create({'name': 'Shared category'})
        cls.category_b = Category.create({'name': 'Category of B', 'company_id': cls.company_b.id})

    def test_requests(self):
        request_b = self.env['hr.request'].create({'employee_id': self.employee_b.id,
                                                   'category_id': self.category_b.id})
        self.assertEqual(request_b.company_id, self.company_b)
        Request = self.env['hr.request'].with_user(self.hr_a)
        self.assertFalse(Request.search([('id', '=', request_b.id)]))
        with self.assertRaises(AccessError):
            request_b.with_user(self.hr_a).read(['name'])
        self.assertIn(self.category, self.env['hr.request.category'].with_user(self.hr_a).search([]),
                      'a category without company is shared')

    def test_no_link_across_companies(self):
        with self.assertRaises(UserError):
            self.env['hr.request'].create({'employee_id': self.employee_a.id, 'category_id': self.category_b.id})
        with self.assertRaises(UserError):
            self.env['hr.request'].create({'employee_id': self.employee_b.id, 'category_id': self.category.id,
                                           'company_id': self.company_a.id})
