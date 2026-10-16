from datetime import date

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestAssetMultiCompany(TransactionCase):
    """ An asset of a company is handed over to the employees of that company; an asset without company to
    anyone. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Asset Company B'})
        cls.manager = new_test_user(cls.env, 'om_asset_mc_manager',
                                    groups='base.group_user,maintenance.group_equipment_manager',
                                    company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        Employee = cls.env['hr.employee']
        cls.employee_a = Employee.create({'name': 'Holder A'})
        cls.employee_b = Employee.with_company(cls.company_b).create({'name': 'Holder B',
                                                                       'company_id': cls.company_b.id})
        Equipment = cls.env['maintenance.equipment']
        cls.laptop_b = Equipment.with_company(cls.company_b).create({'name': 'Laptop B',
                                                                    'company_id': cls.company_b.id})
        cls.shared_phone = Equipment.create({'name': 'Shared Phone', 'company_id': False})

    def assignment(self, equipment, employee):
        return self.env['hr.asset.assignment'].create({'equipment_id': equipment.id, 'employee_id': employee.id,
                                                       'date_from': date(2026, 6, 1)})

    def test_other_company_hidden(self):
        assignment_b = self.assignment(self.laptop_b, self.employee_b)
        self.assertEqual(assignment_b.company_id, self.company_b)
        Assignment = self.env['hr.asset.assignment'].with_user(self.manager)
        self.assertFalse(Assignment.search([('id', '=', assignment_b.id)]))
        with self.assertRaises(AccessError):
            assignment_b.with_user(self.manager).read(['state'])

    def test_no_link_across_companies(self):
        with self.assertRaises(UserError):
            self.assignment(self.laptop_b, self.employee_a)

    def test_shared_asset(self):
        self.assertTrue(self.assignment(self.shared_phone, self.employee_a))
        self.assertTrue(self.assignment(self.shared_phone, self.employee_b))
