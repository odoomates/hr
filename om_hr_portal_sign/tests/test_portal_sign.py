from odoo import Command
from odoo.tests import tagged
from odoo.tools.binary import BinaryBytes

from odoo.addons.om_hr_portal.tests.common import HrPortalCase
from odoo.addons.om_sign.tests.common import blank_pdf


@tagged('post_install', '-at_install')
class TestPortalSign(HrPortalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Policy = cls.env['hr.policy'].with_user(cls.hr_user)
        cls.agree = Policy.create({'name': 'IT Use', 'audience': 'employee',
                                   'employee_ids': [Command.set(cls.employee.ids)]})
        Version = cls.env['hr.policy.version']
        cls.agree_version = Version.create({'policy_id': cls.agree.id, 'body': '<p>Lock your screen.</p>'})
        cls.sign = Policy.create({'name': 'NDA', 'answer_type': 'sign', 'audience': 'employee',
                                  'employee_ids': [Command.set(cls.employee.ids)]})
        cls.sign_version = Version.create({
            'policy_id': cls.sign.id, 'content_type': 'pdf', 'document_file': BinaryBytes(blank_pdf()),
            'document_filename': 'nda.pdf'})
        cls.theirs = Policy.create({'name': 'Colleague Rules', 'audience': 'employee',
                                    'employee_ids': [Command.set(cls.colleague.ids)]})
        cls.theirs_version = Version.create({'policy_id': cls.theirs.id, 'body': '<p>Not yours.</p>'})
        (cls.agree_version | cls.sign_version | cls.theirs_version).with_user(cls.hr_user).action_publish()

    def test_read_and_agree(self):
        assignment = self.agree_version.assignment_ids
        self.assertIn('/my/hr/policies/%s' % assignment.id, assignment._get_my_url(), 'the email leads to the portal')
        self.login_employee()
        self.assertIn('/my/hr/policies', self.get('/my/hr').text)
        page = self.get('/my/hr/policies').text
        self.assertIn('IT Use', page)
        self.assertIn('NDA', page)
        self.assertNotIn('Colleague Rules', page)
        self.assertIn('Lock your screen.', self.get('/my/hr/policies/%s' % assignment.id).text)
        self.url_open('/my/hr/policies/%s/agree' % assignment.id, data={'csrf_token': self.csrf_token()})
        self.assertEqual((assignment.state, assignment.done_by_id), ('done', self.portal_user))
        self.assertIn('Answered on', self.get('/my/hr/policies/%s' % assignment.id).text)

    def test_signed_policy(self):
        assignment = self.sign_version.assignment_ids
        self.login_employee()
        page = self.get('/my/hr/policies/%s' % assignment.id).text
        self.assertIn(assignment._get_signer()._get_sign_url(), page)
        document = self.get('/my/hr/policies/%s/document' % assignment.id)
        self.assertTrue(document.content.startswith(b'%PDF'))
        response = self.url_open('/my/hr/policies/%s/agree' % assignment.id, data={'csrf_token': self.csrf_token()})
        self.assertIn('to be signed', response.text)
        self.assertEqual(assignment.state, 'pending')

    def test_no_one_else_s_policy(self):
        theirs = self.theirs_version.assignment_ids
        self.login_employee()
        self.assertEqual(self.get('/my/hr/policies/%s' % theirs.id).status_code, 404)
        self.assertEqual(self.get('/my/hr/policies/%s/document' % theirs.id).status_code, 404)
        response = self.url_open('/my/hr/policies/%s/agree' % theirs.id, data={'csrf_token': self.csrf_token()})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(theirs.state, 'pending')
