from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.om_sign.tests.common import SIGNATURE


@tagged('post_install', '-at_install')
class TestPreboardingOffer(TransactionCase):

    def accepted_applicant(self, name, email):
        recruiter = new_test_user(self.env, 'om_pb_offer_%s' % name.lower(), email='%s.r@example.com' % name.lower(),
                                  groups='base.group_user,hr_recruitment.group_hr_recruitment_user')
        hr_manager = new_test_user(self.env, 'om_pb_offer_hrm_%s' % name.lower(),
                                   email='%s.m@example.com' % name.lower(),
                                   groups='base.group_user,hr.group_hr_manager')
        applicant = self.env['hr.applicant'].create({'partner_name': name, 'email_from': email})
        start = fields.Date.today() + timedelta(days=20)
        offer = self.env['hr.applicant.offer'].with_user(recruiter).create({
            'applicant_id': applicant.id, 'job_id': self.env['hr.job'].create({'name': 'Clerk %s' % name}).id,
            'wage': 3000.0, 'date_start': start, 'trial_date_end': start + timedelta(days=90)})
        offer.action_submit()
        offer.with_user(hr_manager).action_approval_approve()
        offer.with_user(recruiter).action_send()
        for signer in offer.sign_request_id.signer_ids.sudo():
            signer._sign(signer.partner_id.name, SIGNATURE)
        self.assertEqual(offer.state, 'accepted')
        return applicant, offer

    def test_starts_from_the_offer(self):
        self.env.company.preboarding_from_offer = True
        applicant, offer = self.accepted_applicant('Olga', 'olga@example.com')
        applicant.create_employee_from_applicant()
        preboarding = self.env['hr.preboarding'].search([('employee_id', '=', applicant.employee_id.id)])
        self.assertEqual((preboarding.state, preboarding.date_start), ('running', offer.date_start))

    def test_setting_off(self):
        self.env.company.preboarding_from_offer = False
        applicant, _offer = self.accepted_applicant('Omar', 'omar@example.com')
        applicant.create_employee_from_applicant()
        self.assertFalse(self.env['hr.preboarding'].search([('employee_id', '=', applicant.employee_id.id)]))
