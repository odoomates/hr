from datetime import date

from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalCase


@tagged('post_install', '-at_install')
class TestPortalDocument(HrPortalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        passport = cls.env.ref('om_hr_document.document_type_passport')
        Document = cls.env['document.document']
        cls.own = Document.create({'res_model': 'hr.employee', 'res_id': cls.employee.id, 'type_id': passport.id,
                                   'number': 'P-OWN-1', 'date_expiry': date(2030, 1, 1)})
        cls.theirs = Document.create({'res_model': 'hr.employee', 'res_id': cls.colleague.id,
                                      'type_id': passport.id, 'number': 'P-THEIRS-1'})

    def test_list_upload_and_download(self):
        self.login_employee()
        page = self.get('/my/hr/documents')
        self.assertIn('P-OWN-1', page.text)
        self.assertNotIn('P-THEIRS-1', page.text)
        self.url_open('/my/hr/documents/%s/upload' % self.own.id, data={'csrf_token': self.csrf_token()},
                      files={'file': ('renewed.pdf', b'%PDF-1.4 renewed', 'application/pdf')})
        attachment = self.own.attachment_ids
        self.assertEqual(attachment.name, 'renewed.pdf')
        file = self.get('/my/hr/documents/%s/files/%s' % (self.own.id, attachment.id))
        self.assertEqual((file.status_code, file.content), (200, b'%PDF-1.4 renewed'))

    def test_no_one_else_s_document(self):
        self.login_employee()
        response = self.url_open('/my/hr/documents/%s/upload' % self.theirs.id, data={'csrf_token': self.csrf_token()},
                                 files={'file': ('x.pdf', b'x', 'application/pdf')})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.theirs.attachment_ids)
