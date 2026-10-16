from datetime import date, timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.om_sign.tests.common import SIGNATURE


@tagged('post_install', '-at_install')
class TestOffer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.recruiter = new_test_user(cls.env, 'om_offer_recruiter', email='recruiter@example.com',
                                      groups='base.group_user,hr_recruitment.group_hr_recruitment_user')
        cls.hr_manager = new_test_user(cls.env, 'om_offer_hr_manager', email='hrm@example.com',
                                       groups='base.group_user,hr.group_hr_manager')
        cls.outsider = new_test_user(cls.env, 'om_offer_outsider', groups='base.group_user')
        cls.job = cls.env['hr.job'].create({'name': 'Warehouse Lead'})
        cls.department = cls.env['hr.department'].create({'name': 'Logistics'})
        cls.employee_type = cls.env['hr.employee.type'].create({'name': 'Permanent'})
        cls.applicant = cls.env['hr.applicant'].create({
            'partner_name': 'Carla Candidate', 'email_from': 'carla@example.com', 'job_id': cls.job.id,
            'department_id': cls.department.id, 'salary_expected': 4200.0})

    def offer(self, **values):
        return self.env['hr.applicant.offer'].with_user(self.recruiter).create({
            'applicant_id': self.applicant.id, 'job_id': self.job.id, 'department_id': self.department.id,
            'wage': 4000.0, 'date_start': date(2026, 12, 1), 'trial_date_end': date(2027, 2, 28),
            'employee_type_id': self.employee_type.id, 'benefits': 'A company phone.', **values})

    def approved_offer(self):
        offer = self.offer()
        offer.action_submit()
        self.assertEqual(offer.state, 'to_approve')
        offer.with_user(self.hr_manager).action_approval_approve()
        self.assertEqual(offer.state, 'approved')
        return offer

    def signer(self, offer, role):
        return offer.sign_request_id.signer_ids.filtered(lambda signer: signer.role_name == role).sudo()

    def test_offer_accepted_and_employee_created(self):
        action = self.applicant.with_user(self.recruiter).action_new_offer()
        self.assertEqual(action['context']['default_wage'], 4200.0)
        offer = self.approved_offer()
        with self.assertRaises(UserError):
            offer.with_user(self.recruiter).wage = 5000.0
        offer.with_user(self.recruiter).action_send()
        self.assertEqual(offer.state, 'sent')
        self.assertTrue(self.applicant.partner_id, 'the candidate gets a contact, as core does')
        self.assertEqual(offer.issue_id.state, 'issued')
        self.assertIn(b'Warehouse Lead', offer.issue_id.attachment_id.raw.content)
        sign_request = offer.sign_request_id
        self.assertEqual(sign_request.date_deadline, offer.date_valid)
        company, candidate = self.signer(offer, 'Company'), self.signer(offer, 'Candidate')
        self.assertEqual(company.partner_id, self.recruiter.partner_id, 'the company signs first')
        self.assertEqual(candidate.partner_id, self.applicant.partner_id)
        self.assertEqual((company.state, candidate.state), ('to_sign', 'waiting'))

        company._sign('Rita Recruiter', SIGNATURE)
        candidate._sign('Carla Candidate', SIGNATURE)
        self.assertEqual(offer.state, 'accepted')
        self.assertTrue(self.applicant.stage_id.hired_stage)
        self.assertEqual((self.applicant.salary_proposed, self.applicant.availability), (4000.0, date(2026, 12, 1)))

        self.applicant.with_user(self.hr_manager).sudo().create_employee_from_applicant()
        employee = self.applicant.employee_id
        self.assertEqual(employee.wage, 4000.0)
        self.assertEqual(employee.contract_date_start, date(2026, 12, 1))
        self.assertEqual(employee.trial_date_end, date(2027, 2, 28))
        self.assertEqual(employee.employee_type_id, self.employee_type)
        self.assertEqual((employee.job_id, employee.department_id), (self.job, self.department))

    def test_refused(self):
        offer = self.offer()
        offer.action_submit()
        offer.with_user(self.hr_manager).action_approval_refuse('Too high')
        self.assertEqual(offer.state, 'refused')
        with self.assertRaises(UserError):
            offer.action_send()
        action = offer.action_reset()
        again = self.env['hr.applicant.offer'].browse(action['res_id'])
        self.assertEqual((again.state, again.wage), ('draft', 4000.0))

    def test_declined(self):
        offer = self.approved_offer()
        offer.with_user(self.recruiter).action_send()
        self.signer(offer, 'Company')._sign('Rita', SIGNATURE)
        self.signer(offer, 'Candidate')._decline('I took another job.')
        self.assertEqual((offer.state, offer.decline_reason), ('declined', 'I took another job.'))
        self.assertFalse(self.applicant.stage_id.hired_stage)

    def test_expired_and_withdrawn(self):
        offer = self.approved_offer()
        offer.with_user(self.recruiter).action_send()
        with freeze_time(fields.Date.today() + timedelta(days=8)):
            self.env['sign.request']._cron_remind_and_expire()
        self.assertEqual(offer.state, 'expired')

        other = self.offer()
        other.action_submit()
        other.with_user(self.hr_manager).action_approval_approve()
        other.with_user(self.recruiter).action_send()
        other.with_user(self.recruiter).action_cancel()
        self.assertEqual((other.state, other.sign_request_id.state), ('cancelled', 'cancelled'))

    def test_checks(self):
        with self.assertRaises(UserError):
            self.offer(date_valid=fields.Date.today() - timedelta(days=1)).action_submit()
        with self.assertRaises(UserError):
            self.offer(trial_date_end=date(2026, 11, 1)).action_submit()
        self.applicant.email_from = False
        self.applicant.partner_id.email = False
        offer = self.approved_offer()
        with self.assertRaises(UserError):
            offer.with_user(self.recruiter).action_send()

    def test_access(self):
        offer = self.offer()
        with self.assertRaises(AccessError):
            offer.with_user(self.outsider).read(['wage'])
        self.assertEqual(offer.with_user(self.hr_manager).wage, 4000.0, 'the approvers read the offer')
