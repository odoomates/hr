from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalMultiCompanyCase


@tagged('post_install', '-at_install')
class TestPortalMultiCompany(HrPortalMultiCompanyCase):

    def test_own_company(self):
        self.assertEqual(self.portal_user_b.company_id, self.company_b, 'the portal user of the employee\'s company')
        self.login_employee_b()
        home = self.get('/my/hr').text
        self.assertIn('Portal Employee B', home)
        self.assertNotIn('Portal Employee<', home)
        self.assertNotIn('Storekeeper', self.get('/my/hr/profile').text)
