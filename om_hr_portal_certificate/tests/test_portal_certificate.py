
from odoo import Command
from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalCase


@tagged('post_install', '-at_install')
class TestPortalCertificate(HrPortalCase):

    def test_request_approved_and_downloaded(self):
        self.env.ref('om_hr_certificate.flow_om_hr_certificate_hr').group_id = self.env['res.groups'].create({
            'name': 'Portal Certificate Approvers', 'user_ids': [Command.link(self.hr_user.id)]})
        salary = self.env.ref('om_hr_certificate.template_salary_certificate')
        self.login_employee()
        self.assertIn('Salary Certificate', self.get('/my/hr/certificates').text)
        self.url_open('/my/hr/certificates/new', data={
            'csrf_token': self.csrf_token(), 'template_id': salary.id, 'addressee': 'Portal Bank',
            'purpose': 'Account'})
        certificate = self.env['hr.certificate'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual(certificate.state, 'to_approve')
        self.assertEqual(self.get('/my/hr/certificates/%s/pdf' % certificate.id).status_code, 404, 'not yet')

        certificate.with_user(self.manager_user).action_approval_approve()
        certificate.with_user(self.hr_user).action_approval_approve()
        self.assertEqual(certificate.state, 'issued')
        pdf = self.get('/my/hr/certificates/%s/pdf' % certificate.id)
        self.assertEqual((pdf.status_code, pdf.headers['Content-Type']), (200, 'application/pdf'))

        self.authenticate(self.colleague_user.login, self.colleague_user.login)
        self.assertEqual(self.get('/my/hr/certificates/%s/pdf' % certificate.id).status_code, 404)
