from datetime import date

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestGratuity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.resigned = cls.env.ref('hr.departure_resigned')
        cls.fired = cls.env.ref('hr.departure_fired')
        cls.scheme = cls.env['om.hr.gratuity.scheme'].create({
            'name': 'Test Scheme', 'sequence': 0, 'min_years': 1, 'days_per_month': 30,
            'band_ids': [Command.create({'from_years': 0, 'to_years': 5, 'days_per_year': 21}),
                         Command.create({'from_years': 5, 'days_per_year': 30})],
            'factor_ids': [
                Command.create({'departure_reason_ids': [Command.link(cls.resigned.id)],
                                'from_years': 0, 'to_years': 3, 'factor': 33.33}),
                Command.create({'departure_reason_ids': [Command.link(cls.resigned.id)],
                                'from_years': 3, 'to_years': 5, 'factor': 66.67}),
            ],
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Long Server', 'date_version': date(2019, 1, 1), 'contract_date_start': date(2019, 1, 1),
            'wage': 3000.0})

    def exit_(self, last_day, reason, start=date(2019, 1, 1)):
        exit_ = self.env['om.hr.exit'].create({
            'employee_id': self.employee.id, 'departure_reason_id': reason.id,
            'date_notice': last_day, 'notice_days': 0, 'gratuity_scheme_id': self.scheme.id,
            'gratuity_date_start': start})
        exit_.action_compute_gratuity()
        return exit_

    def test_bands(self):
        """ 7 years: 5 × 21 + 2 × 30 = 165 days of a 100 a day pay. """
        exit_ = self.exit_(date(2025, 12, 31), self.fired)
        self.assertAlmostEqual(exit_.gratuity_years, 7.0, places=2)
        self.assertAlmostEqual(exit_.gratuity_days, 165.0, places=2)
        self.assertEqual(exit_.gratuity_amount, 16500.0)
        self.assertEqual(exit_.gratuity_wage, 3000.0)

    def test_resignation_keeps_a_part(self):
        exit_ = self.exit_(date(2020, 12, 31), self.resigned)
        self.assertEqual(exit_.gratuity_amount, round(42 * 100 * 0.3333, 2))
        self.assertIn('33.33', exit_.gratuity_explanation)
        self.assertEqual(self.exit_(date(2020, 12, 31), self.fired).gratuity_amount, 4200.0,
                         'a dismissal keeps all of it')
        self.assertEqual(self.exit_(date(2025, 12, 31), self.resigned).gratuity_amount, 16500.0,
                         'beyond the lines of the resignations, all of it is kept')

    def test_minimum_and_cap(self):
        self.assertEqual(self.exit_(date(2019, 6, 30), self.fired).gratuity_amount, 0.0)
        self.scheme.max_months = 2
        self.assertEqual(self.exit_(date(2025, 12, 31), self.fired).gratuity_amount, 6000.0)

    def test_default_scheme(self):
        exit_ = self.env['om.hr.exit'].create({'employee_id': self.employee.id})
        self.assertEqual(exit_.gratuity_scheme_id, self.scheme)
        self.assertEqual(exit_.gratuity_date_start, date(2019, 1, 1))
