from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalMultiCompanyCase


@tagged('post_install', '-at_install')
class TestPortalExitMultiCompany(HrPortalMultiCompanyCase):

    def test_resignation_of_the_company(self):
        self.login_employee_b()
        self.url_open('/my/hr/resignation/new', data={
            'csrf_token': self.csrf_token(), 'note': 'Moving abroad', 'date_notice': '2026-11-02', 'confirm': '1'})
        exit_b = self.env['hr.exit'].search([('employee_id', '=', self.employee_b.id)])
        self.assertEqual(exit_b.company_id, self.company_b)
        self.assertFalse(self.env['hr.exit'].search([('employee_id', '=', self.employee.id)]))
