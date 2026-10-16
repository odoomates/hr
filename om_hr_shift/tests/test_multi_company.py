from datetime import date, timedelta

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestShiftMultiCompany(TransactionCase):
    """ A shift stays in the company of its employee, of a template of that company or a shared one. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Shift Company B'})
        cls.planner = new_test_user(cls.env, 'om_shift_mc_planner',
                                    groups='base.group_user,om_hr_shift.group_shift_planner',
                                    company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        Employee = cls.env['hr.employee']
        cls.employee_a = Employee.create({'name': 'Shift Worker A', 'tz': 'UTC'})
        cls.employee_b = Employee.with_company(cls.company_b).create({'name': 'Shift Worker B', 'tz': 'UTC',
                                                                       'company_id': cls.company_b.id})
        cls.template_b = cls.env['hr.shift.template'].create({'name': 'Late B', 'code': 'LB', 'hour_from': 14.0,
                                                              'hour_to': 22.0, 'company_id': cls.company_b.id})
        cls.morning = cls.env.ref('om_hr_shift.template_morning')
        cls.day = date.today() + timedelta(days=30)

    def shift(self, template, employee):
        Shift = self.env['hr.shift'].with_context(om_shift_override=True)
        return Shift.create(dict(template._shift_values(), employee_id=employee.id, date=self.day))

    def test_other_company_hidden(self):
        shift_a, shift_b = self.shift(self.morning, self.employee_a), self.shift(self.morning, self.employee_b)
        self.assertEqual((shift_a.company_id, shift_b.company_id), (self.company_a, self.company_b))
        Shift = self.env['hr.shift'].with_user(self.planner)
        self.assertEqual(Shift.search([('id', 'in', (shift_a | shift_b).ids)]), shift_a)
        with self.assertRaises(AccessError):
            shift_b.with_user(self.planner).read(['date'])

    def test_no_link_across_companies(self):
        with self.assertRaises(UserError):
            self.shift(self.template_b, self.employee_a)

    def test_shared_template(self):
        self.assertFalse(self.morning.company_id)
        self.assertTrue(self.shift(self.morning, self.employee_a))
        self.assertTrue(self.shift(self.morning, self.employee_b))
