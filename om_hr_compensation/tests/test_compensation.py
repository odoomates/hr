from datetime import date

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestCompensation(TransactionCase):
    """ Salary grades, the compa-ratio of each wage, and a merit cycle from the budgets to the new versions. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_user = new_test_user(cls.env, 'om_comp_hr', groups='base.group_user,hr.group_hr_manager')
        cls.manager_user = new_test_user(cls.env, 'om_comp_manager', groups='base.group_user')
        cls.other_user = new_test_user(cls.env, 'om_comp_other', groups='base.group_user')
        cls.grade = cls.env['hr.salary.grade'].create({'name': 'Comp G4', 'wage_min': 4000, 'wage_max': 6000})
        cls.job = cls.env['hr.job'].create({'name': 'Comp Developer', 'salary_grade_id': cls.grade.id})
        cls.department = cls.env['hr.department'].create({'name': 'Comp Department'})
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': 'Comp Manager', 'user_id': cls.manager_user.id})
        cls.low = Employee.create({
            'name': 'Comp Low', 'parent_id': cls.manager.id, 'department_id': cls.department.id,
            'job_id': cls.job.id, 'wage': 4500, 'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1)})
        cls.high = Employee.create({
            'name': 'Comp High', 'parent_id': cls.manager.id, 'department_id': cls.department.id,
            'job_id': cls.job.id, 'wage': 5500, 'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1)})

    def test_band_and_compa_ratio(self):
        self.assertEqual(self.grade.wage_mid, 5000)
        version = self.low.version_id
        self.assertAlmostEqual(version.compa_ratio, 0.9)
        self.assertEqual(version.band_position, 'lower')
        self.assertEqual(self.high.version_id.band_position, 'upper')
        version.wage = 6500
        self.assertEqual(version.band_position, 'above')
        self.grade.wage_mid = 5200
        self.assertAlmostEqual(version.compa_ratio, 1.25, msg='Follows the midpoint of the grade')
        with self.assertRaises(ValidationError):
            self.grade.wage_min = 7000
        action = self.env['hr.version'].with_user(self.hr_user).action_open_pay_position()
        self.assertIn(version.id, self.env['hr.version'].search(action['domain']).ids)

    def test_merit_cycle(self):
        cycle = self.env['hr.merit.cycle'].with_user(self.hr_user).create({
            'name': 'Comp Merit', 'date_effective': date(2027, 1, 1), 'budget_percent': 4.0,
            'department_ids': [(4, self.department.id)]})
        cycle.action_generate()
        self.assertEqual(cycle.line_ids.employee_id, self.low | self.high)
        budget = cycle.budget_ids
        self.assertEqual((budget.payroll, budget.budget), (10000, 400))
        with self.assertRaises(AccessError):
            cycle.line_ids.with_user(self.manager_user).read(['current_wage'])  # not open yet
        cycle.action_open()
        self.assertEqual(cycle.activity_ids.user_id, self.manager_user)

        low, high = (cycle.line_ids.filtered(lambda line, e=employee: line.employee_id == e)
                     for employee in (self.low, self.high))
        as_manager = low.with_user(self.manager_user)
        as_manager.proposed_percent = 6.0
        self.assertEqual((low.proposed_wage, low.increase), (4770, 270))
        high.with_user(self.manager_user).proposed_wage = 5610
        self.assertAlmostEqual(high.proposed_percent, 2.0)
        self.assertEqual(budget.remaining, 20)
        with self.assertRaises(UserError):
            high.with_user(self.manager_user).proposed_wage = 5700  # 70 over the budget
        with self.assertRaises(AccessError):
            as_manager.state = 'approved'
        with self.assertRaises(AccessError):
            low.with_user(self.other_user).read(['current_wage'])

        cycle.action_review()
        with self.assertRaises(UserError):
            as_manager.proposed_percent = 1.0  # the proposals are closed
        high.action_refuse()
        cycle.action_approve_all()
        cycle.action_apply()
        self.assertEqual(cycle.state, 'done')
        self.assertEqual((low.version_id.date_version, low.version_id.wage), (date(2027, 1, 1), 4770))
        self.assertEqual(self.low.version_id.wage, 4500, 'The current version stays until the effective date')
        self.assertFalse(high.version_id, 'A refused raise changes nothing')
