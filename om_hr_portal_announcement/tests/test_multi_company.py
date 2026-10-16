from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalMultiCompanyCase


@tagged('post_install', '-at_install')
class TestPortalAnnouncementMultiCompany(HrPortalMultiCompanyCase):

    def test_announcements_of_the_company(self):
        Announcement = self.env['hr.announcement'].with_user(self.hr_user)
        company_a = Announcement.create({'name': 'Company A news', 'body': '<p>A</p>', 'company_id': self.company_a.id})
        company_b = Announcement.create({'name': 'Company B news', 'body': '<p>B</p>', 'company_id': self.company_b.id})
        (company_a | company_b).action_publish()
        self.assertNotIn(self.employee_b, company_a.recipient_ids.employee_id)
        self.login_employee_b()
        page = self.get('/my/hr/announcements').text
        self.assertIn('Company B news', page)
        self.assertNotIn('Company A news', page)
        self.assertEqual(self.get('/my/hr/announcements/%s' % company_a.id).status_code, 404)
