from datetime import date

from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import OmHrPortalCase


@tagged('post_install', '-at_install')
class TestPortalLeave(OmHrPortalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.annual = cls.env['hr.work.entry.type'].create({
            'name': 'Portal Annual Leave', 'code': 'PORTALANNUAL', 'count_as': 'absence', 'requires_allocation': True,
            'time_off_selectable': True, 'request_unit': 'day', 'unit_of_measure': 'day'})
        allocation = cls.env['hr.leave.allocation'].create({
            'name': 'Annual', 'employee_id': cls.employee.id, 'work_entry_type_id': cls.annual.id,
            'number_of_days': 20, 'date_from': date(2026, 1, 1)})
        allocation.action_approve()
        cls.colleague_leave = cls.env['hr.leave'].create({
            'employee_id': cls.colleague.id, 'work_entry_type_id': cls.env['hr.work.entry.type'].create({
                'name': 'Portal Unpaid', 'code': 'PORTALUNPAID', 'count_as': 'absence', 'requires_allocation': False,
                'time_off_selectable': True}).id,
            'request_date_from': date(2026, 11, 2), 'request_date_to': date(2026, 11, 2)})

    def test_balance_request_and_withdraw(self):
        self.login_employee()
        page = self.get('/my/hr/time-off')
        self.assertIn('Portal Annual Leave', page.text)
        self.assertIn('of 20', page.text)

        response = self.url_open('/my/hr/time-off/new', data={
            'csrf_token': self.csrf_token(), 'work_entry_type_id': self.annual.id,
            'date_from': '2026-11-09', 'date_to': '2026-11-10', 'name': 'Family visit'}, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        leave = self.env['hr.leave'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual((leave.state, leave.number_of_days, leave.name), ('confirm', 2, 'Family visit'))

        self.url_open('/my/hr/time-off/%s/cancel' % leave.id, data={'csrf_token': self.csrf_token()})
        self.assertFalse(leave.exists(), 'a request not approved yet is withdrawn')

    def test_errors_are_shown(self):
        self.login_employee()
        page = self.url_open('/my/hr/time-off/new', data={
            'csrf_token': self.csrf_token(), 'work_entry_type_id': self.annual.id,
            'date_from': '2026-11-10', 'date_to': '2026-11-09'})
        self.assertIn('Give the first and the last day', page.text)

    def test_no_one_else_s_time_off(self):
        self.login_employee()
        self.assertNotIn('2026-11-02', self.get('/my/hr/time-off').text)
        response = self.url_open('/my/hr/time-off/%s/cancel' % self.colleague_leave.id,
                                 data={'csrf_token': self.csrf_token()})
        self.assertEqual(response.status_code, 404)
        self.assertTrue(self.colleague_leave.exists())
