from datetime import date

from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestHrFigures(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.department = cls.env['hr.department'].create({'name': 'Figures Department'})
        Employee = cls.env['hr.employee']
        cls.stayer = Employee.create({
            'name': 'Figures Stayer', 'department_id': cls.department.id,
            'date_version': date(2020, 1, 1), 'contract_date_start': date(2020, 1, 1)})
        cls.joiner = Employee.create({
            'name': 'Figures Joiner', 'department_id': cls.department.id,
            'date_version': date(2026, 3, 1), 'contract_date_start': date(2026, 3, 1)})
        cls.leaver = Employee.create({
            'name': 'Figures Leaver', 'department_id': cls.department.id,
            'date_version': date(2024, 1, 1), 'contract_date_start': date(2024, 1, 1),
            'contract_date_end': date(2026, 4, 30)})
        cls.leaver.active = False

    def fetch(self, measure, date_from, date_to, departments='Figures Department'):
        return self.env['hr.version'].om_spreadsheet_fetch_hr([{
            'measure': measure, 'date_from': date_from, 'date_to': date_to, 'departments': departments,
        }])[0]['value']

    def test_headcount_on_a_date(self):
        self.assertEqual(self.fetch('headcount', False, '2026-01-31'), 2, 'the stayer and the leaver')
        self.assertEqual(self.fetch('headcount', False, '2026-04-30'), 3)
        self.assertEqual(self.fetch('headcount', False, '2026-05-01'), 2, 'the leaver left, archived')
        self.assertEqual(self.fetch('headcount', False, '2019-12-31'), 0)

    def test_joiners_and_leavers(self):
        self.assertEqual(self.fetch('joiners', '2026-01-01', '2026-12-31'), 1)
        self.assertEqual(self.fetch('leavers', '2026-01-01', '2026-12-31'), 1)
        self.assertEqual(self.fetch('leavers', '2026-05-01', '2026-12-31'), 0)

    def test_tenure(self):
        """ On 2026-01-01: the stayer 6 years, the leaver 2 years. """
        self.assertAlmostEqual(self.fetch('tenure', False, '2026-01-01'), 4.0, places=1)

    def test_department_filter(self):
        self.assertEqual(self.fetch('headcount', False, '2026-04-30', departments='Another Department'), 0)

    def test_hr_only(self):
        user = new_test_user(self.env, 'om_figures_plain', groups='base.group_user')
        # the batch of the spreadsheet gives the error to the formula instead of raising it
        result = self.env['hr.version'].with_user(user).om_spreadsheet_fetch_hr(
            [{'measure': 'headcount', 'date_to': '2026-01-01'}])
        self.assertIn('__error__', result[0])
        self.assertNotIn('value', result[0])


@tagged('post_install', '-at_install')
class TestWorkforceDashboard(HttpCase):

    def test_workforce_dashboard(self):
        self.env['hr.employee'].create({'name': 'Dashboard Employee', 'date_version': date(2025, 1, 1),
                                        'contract_date_start': date(2025, 1, 1)})
        self.start_tour('/odoo/action-spreadsheet_dashboard.ir_actions_dashboard_action', 'om_spreadsheet_hr_workforce',
                        login='admin')
