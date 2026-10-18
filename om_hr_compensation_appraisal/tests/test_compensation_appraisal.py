from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCompensationAppraisal(TransactionCase):
    """ A merit cycle reads the last rating of each employee and suggests their raise from the merit matrix. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        grade = cls.env['hr.salary.grade'].create({'name': 'Merit G4', 'wage_min': 4000, 'wage_max': 6000})
        job = cls.env['hr.job'].create({'name': 'Merit Developer', 'salary_grade_id': grade.id})
        Employee = cls.env['hr.employee']
        values = {'job_id': job.id, 'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1)}
        cls.rated = Employee.create(dict(values, name='Merit Rated', wage=4200))
        cls.unrated = Employee.create(dict(values, name='Merit Unrated', wage=5000))
        Appraisal = cls.env['hr.appraisal']
        old = Appraisal.create({'employee_id': cls.rated.id})
        old.sudo().write({'state': 'done', 'date_done': date(2025, 6, 1),
                          'rating_id': cls.env.ref('om_hr_appraisal.rating_meets').id})
        last = Appraisal.create({'employee_id': cls.rated.id})
        last.sudo().write({'state': 'done', 'date_done': date(2026, 6, 1),
                           'rating_id': cls.env.ref('om_hr_appraisal.rating_exceeds').id})

    def test_rating_and_suggested_raise(self):
        cycle = self.env['hr.merit.cycle'].create({'name': 'Merit Matrix Cycle', 'date_effective': date(2027, 1, 1)})
        cycle.action_generate()
        rated = cycle.line_ids.filtered(lambda line: line.employee_id == self.rated)
        unrated = cycle.line_ids.filtered(lambda line: line.employee_id == self.unrated)
        self.assertEqual(rated.rating_id, self.env.ref('om_hr_appraisal.rating_exceeds'), 'The last rating')
        self.assertEqual(rated.band_position, 'lower')
        self.assertEqual(rated.proposed_percent, 5.0, 'Exceeds, in the lower third of the band')
        self.assertEqual(rated.proposed_wage, 4410)
        self.assertFalse(unrated.rating_id)
        self.assertEqual(unrated.proposed_percent, 0.0, 'No rating, no suggestion')

        # a company matrix wins over the shared one
        self.env['hr.merit.matrix'].create({
            'rating_id': self.env.ref('om_hr_appraisal.rating_exceeds').id, 'band_position': 'lower',
            'percent': 5.5, 'company_id': self.env.company.id})
        cycle.line_ids.unlink()
        cycle.action_generate()
        self.assertEqual(cycle.line_ids.filtered(lambda line: line.employee_id == self.rated).proposed_percent, 5.5)
