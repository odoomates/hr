from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalMultiCompanyCase


@tagged('post_install', '-at_install')
class TestPortalCertificateMultiCompany(HrPortalMultiCompanyCase):

    def test_templates_and_certificates_of_the_company(self):
        model_id = self.env['ir.model']._get_id('hr.employee')
        Template = self.env['print.template']
        template_a = Template.create({'name': 'Letter of Company A', 'model_id': model_id, 'body_html': '<p>A</p>',
                                      'employee_request': True, 'company_id': self.company_a.id})
        shared = Template.create({'name': 'Shared Letter', 'model_id': model_id, 'body_html': '<p>All</p>',
                                  'employee_request': True})
        certificate_a = self.env['hr.certificate'].create({
            'employee_id': self.employee.id, 'template_id': template_a.id})
        self.login_employee_b()
        page = self.get('/my/hr/certificates').text
        self.assertIn(shared.name, page)
        self.assertNotIn(template_a.name, page)
        self.assertEqual(self.get('/my/hr/certificates/%s/pdf' % certificate_a.id).status_code, 404)
