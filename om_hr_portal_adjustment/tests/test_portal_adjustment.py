from datetime import date

from odoo.tests import new_test_user, tagged

from odoo.addons.om_hr_portal.tests.common import OmHrPortalCase


@tagged('post_install', '-at_install')
class TestPortalAdjustment(OmHrPortalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        officer = new_test_user(cls.env, 'om_portal_adj_officer',
                                groups='base.group_user,om_hr_payroll.group_hr_payroll_user')
        Adjustment = cls.env['om.hr.payroll.adjustment'].with_user(officer)
        fine = cls.env.ref('om_hr_payroll_adjustment.adjustment_type_court')
        values = {'type_id': fine.id, 'amount': 150.0, 'recurrence': 'months', 'month_count': 2,
                  'date_start': date(2026, 11, 1), 'description': 'Court order 42'}
        cls.running = Adjustment.create(dict(values, employee_id=cls.employee.id))
        cls.running.action_confirm()
        cls.draft = Adjustment.create(dict(values, employee_id=cls.employee.id, description='Not yet'))
        cls.colleague_adjustment = Adjustment.create(dict(values, employee_id=cls.colleague.id))
        cls.colleague_adjustment.action_confirm()

    def test_follow(self):
        self.login_employee()
        page = self.get('/my/hr/adjustments')
        self.assertIn(self.running.name, page.text)
        self.assertIn('Court order 42', page.text)
        self.assertNotIn(self.draft.name, page.text, 'a draft stays with the payroll')
        self.assertNotIn(self.colleague_adjustment.name, page.text)
        detail = self.get('/my/hr/adjustments/%s' % self.running.id)
        self.assertIn('November 2026', detail.text)
        self.assertIn('December 2026', detail.text)
        self.assertIn('/my/hr/adjustments', self.get('/my/hr').text)

    def test_no_one_else_s_adjustment(self):
        self.login_employee()
        self.assertEqual(self.get('/my/hr/adjustments/%s' % self.colleague_adjustment.id).status_code, 404)
        self.assertEqual(self.get('/my/hr/adjustments/%s' % self.draft.id).status_code, 404)
