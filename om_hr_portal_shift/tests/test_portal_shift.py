from datetime import date, timedelta

from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalCase


@tagged('post_install', '-at_install')
class TestPortalShift(HrPortalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.day = date.today() + timedelta(days=3)
        department = cls.env['hr.department'].create({'name': 'Portal Floor'})
        (cls.employee | cls.colleague).write({'department_id': department.id, 'tz': 'UTC'})
        morning = cls.env.ref('om_hr_shift.template_morning')
        evening = cls.env.ref('om_hr_shift.template_evening')
        Shift = cls.env['hr.shift'].with_context(om_shift_override=True)
        # the open shifts already there, e.g. of the demo data, are not those of the test
        Shift.search([('employee_id', '=', False)]).unlink()
        cls.mine = Shift.create(dict(morning._shift_values(), employee_id=cls.employee.id, date=cls.day))
        cls.theirs = Shift.create(dict(evening._shift_values(), employee_id=cls.colleague.id,
                                       date=cls.day + timedelta(days=1)))
        cls.open_shift = Shift.create(dict(evening._shift_values(), date=cls.day + timedelta(days=2),
                                           department_id=department.id))
        cls.draft = Shift.create(dict(evening._shift_values(), employee_id=cls.employee.id,
                                      date=cls.day + timedelta(days=3)))
        (cls.mine | cls.theirs | cls.open_shift).action_publish()

    def test_my_shifts(self):
        self.login_employee()
        page = self.get('/my/hr/shifts').text
        self.assertIn(self.day.strftime('%a %d %b'), page)
        self.assertNotIn((self.day + timedelta(days=3)).strftime('%a %d %b'), page, 'a draft is not shown')
        self.assertIn('/my/hr/shifts', self.get('/my/hr').text)

    def test_claim_and_swap(self):
        self.login_employee()
        self.url_open('/my/hr/shifts/claim', data={'csrf_token': self.csrf_token(), 'shift_id': self.open_shift.id})
        claim = self.env['hr.shift.request'].search([('kind', '=', 'claim'), ('employee_id', '=', self.employee.id)])
        self.assertEqual((claim.shift_id, claim.state), (self.open_shift, 'to_approve'))
        self.url_open('/my/hr/shifts/swap', data={'csrf_token': self.csrf_token(), 'shift_id': self.mine.id,
                                                  'target_shift_id': self.theirs.id})
        swap = self.env['hr.shift.request'].search([('kind', '=', 'swap'), ('employee_id', '=', self.employee.id)])
        self.assertEqual((swap.target_shift_id, swap.state), (self.theirs, 'to_accept'))
        # the employee cannot answer for the colleague
        self.assertEqual(self.url_open('/my/hr/shifts/requests/%s/accept' % swap.id,
                                       data={'csrf_token': self.csrf_token()}).status_code, 404)
        self.authenticate(self.colleague_user.login, self.colleague_user.login)
        self.assertIn('Swaps Asked of You', self.get('/my/hr/shifts').text)
        self.url_open('/my/hr/shifts/requests/%s/accept' % swap.id, data={'csrf_token': self.csrf_token()})
        self.assertEqual(swap.state, 'to_approve', 'accepted: the manager approves now')

    def test_no_swap_of_someone_else_s_shift(self):
        self.login_employee()
        response = self.url_open('/my/hr/shifts/swap', data={
            'csrf_token': self.csrf_token(), 'shift_id': self.theirs.id, 'target_shift_id': self.mine.id})
        self.assertEqual(response.status_code, 404)

    def test_unavailability(self):
        self.login_employee()
        self.url_open('/my/hr/shifts/unavailable', data={
            'csrf_token': self.csrf_token(), 'date_from': str(self.day), 'reason': 'Wedding'})
        unavailable = self.env['hr.shift.unavailability'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual((unavailable.date_to, unavailable.reason), (self.day, 'Wedding'))
        self.assertIn('Wedding', self.mine.warning)
        other = self.env['hr.shift.unavailability'].create({'employee_id': self.colleague.id,
                                                               'date_from': self.day, 'date_to': self.day})
        response = self.url_open('/my/hr/shifts/unavailable/%s/delete' % other.id,
                                 data={'csrf_token': self.csrf_token()})
        self.assertEqual(response.status_code, 404)
        self.url_open('/my/hr/shifts/unavailable/%s/delete' % unavailable.id, data={'csrf_token': self.csrf_token()})
        self.assertFalse(unavailable.exists())
