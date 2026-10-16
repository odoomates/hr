from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestMultiCompany(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Pre-boarding Company B'})
        cls.hr_a = new_test_user(cls.env, 'om_mc_preboarding_hr_a', groups='base.group_user,hr.group_hr_user',
                                 company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        Employee = cls.env['hr.employee']
        cls.colleague_a = Employee.create({'name': 'Buddy A', 'company_id': cls.company_a.id})
        cls.new_hire_a = Employee.create({'name': 'New A', 'company_id': cls.company_a.id})
        cls.new_hire_b = Employee.create({'name': 'New B', 'company_id': cls.company_b.id})
        cls.first_day = fields.Date.today() + timedelta(days=10)

    def preboarding(self, employee, **values):
        return self.env['hr.preboarding'].create({
            'employee_id': employee.id, 'date_start': self.first_day,
            'line_ids': [Command.create({'name': 'Your emergency contact', 'kind': 'emergency'})], **values})

    def test_preboardings_and_their_steps(self):
        preboarding_b = self.preboarding(self.new_hire_b)
        line = preboarding_b.line_ids
        self.assertEqual((preboarding_b.company_id, line.company_id), (self.company_b, self.company_b),
                         'the steps follow their pre-boarding')
        self.assertFalse(self.env['hr.preboarding'].with_user(self.hr_a).search([('id', '=', preboarding_b.id)]))
        self.assertFalse(self.env['hr.preboarding.line'].with_user(self.hr_a).search([('id', '=', line.id)]))
        with self.assertRaises(AccessError):
            line.with_user(self.hr_a).read(['name'])

    def test_no_buddy_of_another_company(self):
        self.assertTrue(self.preboarding(self.new_hire_a, buddy_id=self.colleague_a.id))
        with self.assertRaises(UserError):
            self.preboarding(self.new_hire_b, buddy_id=self.colleague_a.id)
