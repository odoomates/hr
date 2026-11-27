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
        Shift = cls.env['om.planning.slot']
        # the open shifts already there, e.g. of the demo data, are not those of the test
        Shift.search([('is_open', '=', True)]).unlink()
        cls.mine = Shift.create(morning._shift_values(cls.day, cls.employee))
        cls.theirs = Shift.create(evening._shift_values(cls.day + timedelta(days=1), cls.colleague))
        cls.open_shift = Shift.create(dict(evening._shift_values(cls.day + timedelta(days=2)),
                                           department_id=department.id))
        cls.draft = Shift.create(evening._shift_values(cls.day + timedelta(days=3), cls.employee))
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
        Request = self.env['om.planning.request']
        claim = Request.search([('request_type', '=', 'claim'), ('employee_id', '=', self.employee.id)])
        self.assertEqual((claim.slot_id, claim.state, claim.approval_state), (self.open_shift, 'pending', 'to_approve'))
        self.url_open('/my/hr/shifts/swap', data={'csrf_token': self.csrf_token(), 'shift_id': self.mine.id,
                                                  'target_shift_id': self.theirs.id})
        swap = Request.search([('request_type', '=', 'switch'), ('employee_id', '=', self.employee.id)])
        self.assertEqual((swap.target_slot_id, swap.state), (self.theirs, 'to_accept'))
        # the employee cannot answer for the colleague
        self.assertEqual(self.url_open('/my/hr/shifts/requests/%s/accept' % swap.id,
                                       data={'csrf_token': self.csrf_token()}).status_code, 404)
        self.authenticate(self.colleague_user.login, self.colleague_user.login)
        self.assertIn('Swaps Asked of You', self.get('/my/hr/shifts').text)
        self.url_open('/my/hr/shifts/requests/%s/accept' % swap.id, data={'csrf_token': self.csrf_token()})
        self.assertEqual((swap.state, swap.approval_state), ('pending', 'to_approve'),
                         'accepted: the manager approves now')

    def test_no_swap_of_someone_else_s_shift(self):
        self.login_employee()
        response = self.url_open('/my/hr/shifts/swap', data={
            'csrf_token': self.csrf_token(), 'shift_id': self.theirs.id, 'target_shift_id': self.mine.id})
        self.assertEqual(response.status_code, 404)

    def test_unavailability(self):
        self.login_employee()
        self.url_open('/my/hr/shifts/unavailable', data={
            'csrf_token': self.csrf_token(), 'date_from': str(self.day), 'reason': 'Wedding'})
        Leave = self.env['resource.calendar.leaves']
        unavailable = Leave.search([('resource_id', '=', self.employee.resource_id.id),
                                    ('shift_unavailability', '=', True)])
        self.assertEqual((unavailable.date_to.date(), unavailable.name), (self.day, 'Wedding'))
        self.assertIn('Wedding', self.mine.conflict_info)
        other = Leave.create({'resource_id': self.colleague.resource_id.id, 'shift_unavailability': True,
                              'date_from': unavailable.date_from, 'date_to': unavailable.date_to})
        response = self.url_open('/my/hr/shifts/unavailable/%s/delete' % other.id,
                                 data={'csrf_token': self.csrf_token()})
        self.assertEqual(response.status_code, 404)
        self.url_open('/my/hr/shifts/unavailable/%s/delete' % unavailable.id, data={'csrf_token': self.csrf_token()})
        self.assertFalse(unavailable.exists())
