from datetime import date

from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalCase

@tagged('post_install', '-at_install')
class TestPortalAsset(HrPortalCase):

    def test_own_assets_only(self):
        Equipment = self.env['maintenance.equipment']
        Equipment.create({'name': 'Portal Laptop', 'serial_no': 'SN-PORTAL-OWN', 'employee_id': self.employee.id})
        Equipment.create({'name': 'Portal Phone', 'serial_no': 'SN-PORTAL-THEIRS', 'employee_id': self.colleague.id})
        self.login_employee()
        page = self.get('/my/hr/assets')
        self.assertIn('SN-PORTAL-OWN', page.text)
        self.assertNotIn('SN-PORTAL-THEIRS', page.text)
