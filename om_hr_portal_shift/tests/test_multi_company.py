from datetime import date, timedelta

from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalMultiCompanyCase


@tagged('post_install', '-at_install')
class TestPortalShiftMultiCompany(HrPortalMultiCompanyCase):

    def test_open_shifts_of_the_company(self):
        evening = self.env.ref('om_hr_shift.template_evening')
        Shift = self.env['hr.shift'].with_context(om_shift_override=True)
        Shift.search([('employee_id', '=', False)]).unlink()
        day = date.today() + timedelta(days=4)
        open_a = Shift.create(dict(evening._shift_values(), date=day, company_id=self.company_a.id))
        open_b = Shift.create(dict(evening._shift_values(), date=day, company_id=self.company_b.id))
        (open_a | open_b).action_publish()
        self.login_employee_b()
        page = self.get('/my/hr/shifts').text
        self.assertIn('value="%s"' % open_b.id, page)
        self.assertNotIn('value="%s"' % open_a.id, page)
        self.url_open('/my/hr/shifts/claim', data={'csrf_token': self.csrf_token(), 'shift_id': open_a.id})
        self.assertFalse(self.env['hr.shift.request'].search([('shift_id', '=', open_a.id)]))
