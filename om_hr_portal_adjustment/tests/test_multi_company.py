from datetime import date

from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalMultiCompanyCase


@tagged('post_install', '-at_install')
class TestPortalAdjustmentMultiCompany(HrPortalMultiCompanyCase):

    def test_adjustments_of_the_other_company(self):
        court = self.env.ref('om_hr_payroll_adjustment.adjustment_type_court')
        adjustment_a = self.env['hr.payroll.adjustment'].create({
            'employee_id': self.employee.id, 'type_id': court.id,
            'amount': 150.0, 'recurrence': 'once', 'date_start': date(2026, 11, 1), 'description': 'Company A order'})
        adjustment_a.action_confirm()
        self.login_employee_b()
        self.assertNotIn('Company A order', self.get('/my/hr/adjustments').text)
        self.assertEqual(self.get('/my/hr/adjustments/%s' % adjustment_a.id).status_code, 404)
