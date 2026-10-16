from datetime import date

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestMultiCompany(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'Offers Company B'})
        cls.recruiter_a = new_test_user(
            cls.env, 'om_mc_offer_recruiter_a', groups='base.group_user,hr_recruitment.group_hr_recruitment_user',
            company_id=cls.company_a.id, company_ids=[Command.set(cls.company_a.ids)])
        cls.job_a = cls.env['hr.job'].create({'name': 'Clerk of A', 'company_id': cls.company_a.id})
        cls.job_b = cls.env['hr.job'].create({'name': 'Clerk of B', 'company_id': cls.company_b.id})
        Applicant = cls.env['hr.applicant']
        cls.applicant_a = Applicant.create({'partner_name': 'Candidate A', 'email_from': 'mc.a@example.com',
                                            'job_id': cls.job_a.id, 'company_id': cls.company_a.id})
        cls.applicant_b = Applicant.create({'partner_name': 'Candidate B', 'email_from': 'mc.b@example.com',
                                            'job_id': cls.job_b.id, 'company_id': cls.company_b.id})

    def offer(self, applicant, job):
        return self.env['hr.applicant.offer'].create({
            'applicant_id': applicant.id, 'job_id': job.id, 'wage': 3000.0, 'date_start': date(2027, 1, 4)})

    def test_offers(self):
        offer_b = self.offer(self.applicant_b, self.job_b)
        self.assertEqual(offer_b.company_id, self.company_b, 'an offer takes the company of its applicant')
        self.assertFalse(self.env['hr.applicant.offer'].with_user(self.recruiter_a).search([('id', '=', offer_b.id)]))
        with self.assertRaises(AccessError):
            offer_b.with_user(self.recruiter_a).read(['wage'])

    def test_no_job_of_another_company(self):
        with self.assertRaises(UserError):
            self.offer(self.applicant_a, self.job_b)
