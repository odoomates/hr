from datetime import date, datetime

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestLatenessMultiCompany(TransactionCase):
    """ A lateness stays in the company of its employee, counted along a policy of that company or a shared
    one. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Lateness Company B'})
        cls.officer = new_test_user(cls.env, 'om_lateness_mc_user',
                                    groups='base.group_user,hr_attendance.group_hr_attendance_user',
                                    company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        Employee = cls.env['hr.employee']
        cls.employee_a = Employee.create({'name': 'Late A', 'tz': 'UTC'})
        cls.employee_b = Employee.with_company(cls.company_b).create({'name': 'Late B', 'tz': 'UTC',
                                                                       'company_id': cls.company_b.id})
        Policy = cls.env['hr.lateness.policy']
        cls.policy_b = Policy.create({'name': 'Policy B', 'company_id': cls.company_b.id})
        cls.shared_policy = Policy.create({'name': 'Shared Policy', 'company_id': False})

    def lateness(self, employee, policy):
        return self.env['hr.lateness'].create({
            'employee_id': employee.id, 'policy_id': policy.id, 'date': date(2026, 9, 7), 'kind': 'late_in',
            'scheduled_at': datetime(2026, 9, 7, 8, 0), 'actual_at': datetime(2026, 9, 7, 8, 20), 'minutes': 20})

    def test_other_company_hidden(self):
        lateness_a = self.lateness(self.employee_a, self.shared_policy)
        lateness_b = self.lateness(self.employee_b, self.shared_policy)
        Lateness = self.env['hr.lateness'].with_user(self.officer)
        self.assertEqual(Lateness.search([('id', 'in', (lateness_a | lateness_b).ids)]), lateness_a)
        with self.assertRaises(AccessError):
            lateness_b.with_user(self.officer).read(['minutes'])

    def test_no_link_across_companies(self):
        with self.assertRaises(UserError):
            self.lateness(self.employee_a, self.policy_b)

    def test_shared_policy(self):
        self.assertTrue(self.lateness(self.employee_a, self.shared_policy))
        self.assertTrue(self.lateness(self.employee_b, self.shared_policy))
