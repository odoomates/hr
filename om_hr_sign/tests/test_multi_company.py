from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestMultiCompany(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Policies Company B'})
        cls.hr_a = new_test_user(cls.env, 'om_mc_policy_hr_a', groups='base.group_user,hr.group_hr_user',
                                 company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        Employee = cls.env['hr.employee']
        cls.employee_a = Employee.create({'name': 'Policy A', 'company_id': cls.company_a.id})
        cls.employee_b = Employee.create({'name': 'Policy B', 'company_id': cls.company_b.id})
        Policy = cls.env['hr.policy']
        cls.policy_a = Policy.create({'name': 'Rules of A', 'company_id': cls.company_a.id})
        cls.policy_b = Policy.create({'name': 'Rules of B', 'company_id': cls.company_b.id})
        Version = cls.env['hr.policy.version']
        cls.version_a = Version.create({'policy_id': cls.policy_a.id, 'body': '<p>A</p>'})
        cls.version_b = Version.create({'policy_id': cls.policy_b.id, 'body': '<p>B</p>'})

    def test_policies(self):
        self.assertEqual(self.version_b.company_id, self.company_b, 'a version follows its policy')
        Policy = self.env['hr.policy'].with_user(self.hr_a)
        self.assertEqual(Policy.search([('id', 'in', (self.policy_a | self.policy_b).ids)]), self.policy_a)
        with self.assertRaises(AccessError):
            self.policy_b.with_user(self.hr_a).read(['name'])
        self.version_b.action_publish()
        answers = self.version_b.assignment_ids
        self.assertEqual(answers.employee_id, self.employee_b, 'only the employees of its company are asked')
        self.assertFalse(self.env['hr.policy.assignment'].with_user(self.hr_a).search([('id', 'in', answers.ids)]))

    def test_no_answer_across_companies(self):
        with self.assertRaises(UserError):
            self.env['hr.policy.assignment'].create({'version_id': self.version_a.id,
                                                     'employee_id': self.employee_b.id})
