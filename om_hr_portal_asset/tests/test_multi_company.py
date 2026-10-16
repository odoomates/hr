from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalMultiCompanyCase


@tagged('post_install', '-at_install')
class TestPortalAssetMultiCompany(HrPortalMultiCompanyCase):

    def test_assets_of_the_company(self):
        Equipment = self.env['maintenance.equipment']
        Equipment.create({'name': 'Laptop A', 'serial_no': 'SN-MC-A', 'employee_id': self.employee.id,
                          'company_id': self.company_a.id})
        Equipment.create({'name': 'Laptop B', 'serial_no': 'SN-MC-B', 'employee_id': self.employee_b.id,
                          'company_id': self.company_b.id})
        self.login_employee_b()
        page = self.get('/my/hr/assets').text
        self.assertIn('SN-MC-B', page)
        self.assertNotIn('SN-MC-A', page)
