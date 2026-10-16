from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalMultiCompanyCase


@tagged('post_install', '-at_install')
class TestPortalDocumentMultiCompany(HrPortalMultiCompanyCase):

    def test_documents_of_the_other_company(self):
        passport = self.env.ref('om_hr_document.document_type_passport')
        document_a = self.env['document.document'].create({
            'res_model': 'hr.employee', 'res_id': self.employee.id, 'type_id': passport.id, 'number': 'P-MC-A'})
        document_b = self.env['document.document'].create({
            'res_model': 'hr.employee', 'res_id': self.employee_b.id, 'type_id': passport.id, 'number': 'P-MC-B'})
        self.assertEqual(document_b.company_id, self.company_b)
        self.login_employee_b()
        page = self.get('/my/hr/documents').text
        self.assertIn('P-MC-B', page)
        self.assertNotIn('P-MC-A', page)
        response = self.url_open('/my/hr/documents/%s/upload' % document_a.id, data={'csrf_token': self.csrf_token()},
                                 files={'file': ('passport.pdf', b'%PDF-1.4', 'application/pdf')})
        self.assertEqual(response.status_code, 404)
