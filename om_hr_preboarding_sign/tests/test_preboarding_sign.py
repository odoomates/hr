from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools.binary import BinaryBytes

from odoo.addons.om_sign.tests.common import SIGNATURE, blank_pdf


@tagged('post_install', '-at_install')
class TestPreboardingSign(TransactionCase):

    def test_policies_and_signatures(self):
        hr_user = new_test_user(self.env, 'om_preboarding_sign_hr', groups='base.group_user,hr.group_hr_user',
                                email='hr.sign@example.com')
        Step = self.env['hr.preboarding.step']
        Step.search([]).active = False
        Step.create({'name': 'Policies', 'kind': 'policies', 'sequence': 1})
        Step.create({'name': 'Contract', 'kind': 'signatures', 'sequence': 2})
        policy = self.env['hr.policy'].with_user(hr_user).create({'name': 'Code of Conduct'})
        version = self.env['hr.policy.version'].create({'policy_id': policy.id, 'body': '<p>Be kind.</p>'})
        version.with_user(hr_user).action_publish()
        start = fields.Date.today() + timedelta(days=7)
        employee = self.env['hr.employee'].create({
            'name': 'Sam Signer', 'work_email': 'sam@example.com', 'contract_date_start': start,
            'date_version': start})
        assignment = version.assignment_ids.filtered(lambda a: a.employee_id == employee)
        self.assertTrue(assignment, 'the new employee is asked the policy')
        action = employee.with_user(hr_user).action_start_preboarding()
        preboarding = self.env['hr.preboarding'].browse(action['res_id'])
        policies, contract = preboarding.line_ids.sorted('sequence')
        preboarding._refresh()
        self.assertEqual((policies.state, contract.state), ('todo', 'todo'), 'nothing signed yet')

        assignment.sudo().action_acknowledge()
        sign_request = self.env['sign.request'].with_user(hr_user).create({
            'name': 'Contract', 'document_file': BinaryBytes(blank_pdf()), 'document_filename': 'contract.pdf',
            'signer_ids': [Command.create({'partner_id': employee.work_contact_id.id})]})
        sign_request.action_send()
        preboarding._refresh()
        self.assertEqual((policies.state, contract.state), ('done', 'todo'))
        sign_request.signer_ids.sudo()._sign('Sam Signer', SIGNATURE)
        self.env['hr.preboarding']._cron_follow_up()
        self.assertEqual((contract.state, preboarding.state), ('done', 'done'))
