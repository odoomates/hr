from datetime import date

from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalMultiCompanyCase


@tagged('post_install', '-at_install')
class TestPortalLeaveMultiCompany(HrPortalMultiCompanyCase):

    def test_time_off_of_the_other_company(self):
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee.id, 'work_entry_type_id': self.env['hr.work.entry.type'].create({
                'name': 'Portal MC Unpaid', 'code': 'PORTALMCUNPAID', 'count_as': 'absence',
                'requires_allocation': False, 'time_off_selectable': True}).id,
            'request_date_from': date(2026, 11, 2), 'request_date_to': date(2026, 11, 2)})
        self.login_employee_b()
        response = self.url_open('/my/hr/time-off/%s/cancel' % leave.id, data={'csrf_token': self.csrf_token()})
        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(leave.state, 'cancel')
