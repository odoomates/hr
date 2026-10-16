from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestExitMultiCompany(TransactionCase):
    """ An exit stays in the company of its employee, cleared along the checklist of that company or a shared
    one. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Exit Company B'})
        cls.hr_user = new_test_user(cls.env, 'om_exit_mc_hr', groups='base.group_user,hr.group_hr_user',
                                    company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        Employee = cls.env['hr.employee']
        cls.employee_a = Employee.create({'name': 'Exit Employee A'})
        cls.employee_b = Employee.with_company(cls.company_b).create({'name': 'Exit Employee B',
                                                                       'company_id': cls.company_b.id})
        Checklist = cls.env['hr.exit.checklist']
        cls.item_b = Checklist.create({'name': 'Badge B', 'responsible_type': 'manager',
                                       'company_id': cls.company_b.id})
        cls.shared_item = Checklist.create({'name': 'Handover', 'responsible_type': 'manager'})

    def exit(self, employee):
        return self.env['hr.exit'].create({'employee_id': employee.id})

    def clearance(self, exit_, item):
        return self.env['hr.exit.clearance'].create({'exit_id': exit_.id, 'name': item.name,
                                                     'checklist_id': item.id})

    def test_other_company_hidden(self):
        exit_a, exit_b = self.exit(self.employee_a), self.exit(self.employee_b)
        self.assertEqual((exit_a.company_id, exit_b.company_id), (self.company_a, self.company_b))
        Exit = self.env['hr.exit'].with_user(self.hr_user)
        self.assertEqual(Exit.search([('id', 'in', (exit_a | exit_b).ids)]), exit_a)
        with self.assertRaises(AccessError):
            exit_b.with_user(self.hr_user).read(['state'])

    def test_no_link_across_companies(self):
        with self.assertRaises(UserError):
            self.clearance(self.exit(self.employee_a), self.item_b)

    def test_shared_checklist(self):
        self.assertTrue(self.clearance(self.exit(self.employee_a), self.shared_item))
        self.assertTrue(self.clearance(self.exit(self.employee_b), self.shared_item))
