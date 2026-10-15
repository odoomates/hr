from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged

from .common import OmHrPortalCase


@tagged('post_install', '-at_install')
class TestHrPortal(OmHrPortalCase):

    def test_grant_portal_access(self):
        self.assertTrue(self.portal_user.share, 'a portal user, not a user of the backend')
        self.assertTrue(self.portal_user.has_group('base.group_portal'))
        self.assertEqual(self.portal_user.login, 'portal.employee@example.com')
        with self.assertRaises(UserError):
            self.employee.with_user(self.hr_user).action_om_grant_portal()
        with self.assertRaises(UserError):
            self.colleague.with_user(self.manager_user).action_om_grant_portal()

    def test_home_and_profile(self):
        self.login_employee()
        home = self.get('/my/hr')
        self.assertEqual(home.status_code, 200)
        self.assertIn('Portal Employee', home.text)
        self.assertIn('My Profile', home.text)
        profile = self.get('/my/hr/profile')
        self.assertIn('Storekeeper', profile.text)
        self.assertIn('Portal Manager', profile.text)
        self.assertNotIn('Portal Colleague', profile.text)

    def test_not_an_employee(self):
        new_test_user(self.env, 'om_portal_customer', groups='base.group_portal')
        self.authenticate('om_portal_customer', 'om_portal_customer')
        self.assertEqual(self.get('/my/hr').status_code, 404)

    def test_card_counter(self):
        self.login_employee()
        response = self.make_jsonrpc_request('/my/counters', {'counters': {'om_hr_employee_count': 'common_category'}})
        self.assertEqual(response['om_hr_employee_count'], 1)
