from datetime import date

from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalCase


@tagged('post_install', '-at_install')
class TestPortalExit(HrPortalCase):

    def test_resignation(self):
        self.login_employee()
        page = self.url_open('/my/hr/resignation/new', data={'csrf_token': self.csrf_token(), 'note': 'Moving abroad'})
        self.assertIn('Tick the box', page.text)
        self.url_open('/my/hr/resignation/new', data={
            'csrf_token': self.csrf_token(), 'note': 'Moving abroad', 'date_notice': '2026-11-02', 'confirm': '1'})
        exit_ = self.env['hr.exit'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual((exit_.state, exit_.date_notice), ('to_approve', date(2026, 11, 2)))
        self.assertEqual(exit_.approver_user_ids, self.manager_user)
        page = self.get('/my/hr/resignation')
        self.assertIn(exit_.name, page.text)
        self.assertNotIn('Hand In My Resignation</button>', page.text, 'one exit at a time')
