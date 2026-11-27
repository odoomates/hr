from datetime import UTC, date, datetime, time, timedelta

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.om_hr_shift.models.om_planning_template import shift_segments

MONDAY = date(2026, 9, 7)
UTC = UTC


@tagged('post_install', '-at_install')
class TestShift(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.planner = new_test_user(cls.env, 'om_shift_planner',
                                    groups='base.group_user,om_hr_shift.group_shift_planner')
        cls.manager_user = new_test_user(cls.env, 'om_shift_manager', groups='base.group_user')
        cls.user_a = new_test_user(cls.env, 'om_shift_a', groups='base.group_user')
        cls.user_b = new_test_user(cls.env, 'om_shift_b', groups='base.group_user')
        cls.department = cls.env['hr.department'].create({'name': 'Shift Floor'})
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': 'Shift Manager', 'user_id': cls.manager_user.id})
        values = {'tz': 'UTC', 'parent_id': cls.manager.id, 'department_id': cls.department.id,
                  'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1)}
        cls.employee_a = Employee.create(dict(values, name='Shift A', user_id=cls.user_a.id))
        cls.employee_b = Employee.create(dict(values, name='Shift B', user_id=cls.user_b.id))
        cls.morning = cls.env.ref('om_hr_shift.template_morning')
        cls.evening = cls.env.ref('om_hr_shift.template_evening')
        cls.night = cls.env.ref('om_hr_shift.template_night')
        cls.Shift = cls.env['om.planning.slot'].with_user(cls.planner)
        cls.Request = cls.env['om.planning.request']

    def shift(self, template, day=MONDAY, employee=None, **values):
        employee = self.employee_a if employee is None else employee
        # an open shift in the timezone of the employees of the test
        return self.Shift.create(dict(template.with_context(tz='UTC')._shift_values(day, employee or None), **values))

    def work(self, employee, day):
        """ :return: the work intervals of the employee on the day, as (from, to) in hours """
        start = datetime.combine(day, time.min, UTC)
        stop = datetime.combine(day, time.max, UTC)
        intervals = employee._get_expected_attendances(start, stop)
        def hours(moment):
            # the schedules end a day at 23:59:59.999999
            return 24.0 if (moment.hour, moment.minute) == (23, 59) else round(moment.hour + moment.minute / 60, 2)
        return [(hours(begin), hours(end)) for begin, end, _meta in intervals]

    def test_segments(self):
        monday, tuesday = MONDAY, MONDAY + timedelta(days=1)
        self.assertEqual(shift_segments(datetime(2026, 9, 7, 6), datetime(2026, 9, 7, 14), 10, 0.5),
                         [(monday, 6, 10), (monday, 10.5, 14)])
        self.assertEqual(shift_segments(datetime(2026, 9, 7, 22), datetime(2026, 9, 8, 6), 2, 0.5),
                         [(monday, 22, 24), (tuesday, 0, 2), (tuesday, 2.5, 6)])
        self.assertEqual(shift_segments(datetime(2026, 9, 7, 22), datetime(2026, 9, 8, 6)),
                         [(monday, 22, 24), (tuesday, 0, 6)])
        self.assertEqual(shift_segments(datetime(2026, 9, 7, 8), datetime(2026, 9, 7, 16), 0, 1),
                         [(monday, 8, 11.5), (monday, 12.5, 16)], 'a break outside the shift: in its middle')
        self.assertEqual((self.morning.duration, self.night.duration), (7.5, 7.5))

    def test_start_rostering_keeps_the_past(self):
        before = self.employee_a.version_id.resource_calendar_id
        self.employee_a._start_rostering(date(2026, 9, 1))
        roster = self.employee_a.roster_calendar_id
        self.assertEqual((roster.calendar_type, roster.hours_per_week), ('variable', before.hours_per_week))
        self.assertEqual(self.employee_a._get_version(date(2026, 8, 31)).resource_calendar_id, before)
        self.assertEqual(self.employee_a._get_version(date(2026, 9, 1)).resource_calendar_id, roster)
        self.assertEqual(self.work(self.employee_a, MONDAY), [], 'nothing published: a day off')

    def test_publish_writes_the_schedule(self):
        self.employee_a._start_rostering(date(2026, 9, 1))
        shift = self.shift(self.morning)
        self.assertEqual(self.work(self.employee_a, MONDAY), [], 'a draft is not worked')
        shift.action_publish()
        self.assertEqual(shift.state, 'published')
        self.assertEqual(self.work(self.employee_a, MONDAY), [(6.0, 10.0), (10.5, 14.0)])
        self.assertEqual(len(shift.roster_attendance_ids), 2)
        shift.write({'end_datetime': datetime(2026, 9, 7, 15)})
        self.assertEqual(self.work(self.employee_a, MONDAY), [(6.0, 10.0), (10.5, 15.0)], 'an edit follows')
        shift.resource_ids = self.employee_b.resource_id
        self.assertEqual(self.work(self.employee_a, MONDAY), [])
        self.assertTrue(self.employee_b.roster_calendar_id, 'rostered when given a published shift')
        self.assertEqual(self.work(self.employee_b, MONDAY), [(6.0, 10.0), (10.5, 15.0)])
        shift.action_unpublish()
        self.assertEqual(self.work(self.employee_b, MONDAY), [], 'back to draft: not worked')
        shift.action_publish()
        shift.unlink()
        self.assertEqual(self.work(self.employee_b, MONDAY), [])

    def test_night_shift(self):
        self.employee_a._start_rostering(date(2026, 9, 1))
        night = self.shift(self.night)
        night.action_publish()
        self.assertEqual(night.shift_date, MONDAY)
        self.assertEqual(self.work(self.employee_a, MONDAY), [(22.0, 24.0)])
        self.assertEqual(self.work(self.employee_a, date(2026, 9, 8)), [(0.0, 2.0), (2.5, 6.0)])

    def test_checks(self):
        (self.employee_a | self.employee_b)._start_rostering(date(2026, 9, 1))
        self.employee_a.company_id.write({'planning_min_rest_hours': 11, 'planning_max_hours_week': 48})
        self.env['resource.calendar.leaves'].create({
            'name': 'Holiday Trip', 'resource_id': self.employee_a.resource_id.id,
            'date_from': datetime(2026, 9, 9, 0, 0), 'date_to': datetime(2026, 9, 9, 23, 59)})
        self.env['resource.calendar.leaves'].create({
            'name': 'Exam', 'resource_id': self.employee_a.resource_id.id, 'shift_unavailability': True,
            'date_from': datetime(2026, 9, 10, 0, 0), 'date_to': datetime(2026, 9, 10, 23, 59)})
        evening = self.shift(self.evening)
        morning = self.shift(self.morning, day=date(2026, 9, 8))
        trip = self.shift(self.morning, day=date(2026, 9, 9))
        exam = self.shift(self.morning, day=date(2026, 9, 10))
        overlap = self.shift(self.morning, day=date(2026, 9, 10))
        self.assertFalse(self.shift(self.morning, day=date(2026, 9, 14), employee=self.employee_b).conflict_info,
                         'a rostered employee works their shifts: never outside their schedule')
        self.assertIn('rest', evening.conflict_info)
        self.assertIn('rest', morning.conflict_info, '8 hours between 22:00 and 06:00')
        self.assertIn('Holiday Trip', trip.conflict_info)
        self.assertIn('Exam', exam.conflict_info)
        self.assertIn('already planned', overlap.conflict_info)
        self.employee_a.company_id.planning_max_hours_week = 20
        exam.invalidate_recordset(['conflict_info'])
        self.assertIn('planned in week', exam.conflict_info)
        trip.action_publish()
        self.assertEqual(trip.state, 'published', 'the planner publishes despite the conflicts they see')

    def test_rotation(self):
        rotation = self.env.ref('om_hr_shift.rotation_two_two_two')
        self.assertEqual(rotation.pattern, 'M M N N - -')
        wizard = self.env['om.planning.rotation.apply'].with_user(self.planner).create({
            'rotation_id': rotation.id,
            'resource_ids': [Command.set((self.employee_a | self.employee_b).resource_id.ids)],
            'date_from': MONDAY, 'date_to': date(2026, 9, 12), 'stagger': True, 'skip_leaves': False})
        wizard.action_apply()

        def pattern(employee):
            shifts = self.env['om.planning.slot'].search([('resource_ids', 'in', employee.resource_id.ids)])
            by_day = {shift.shift_date: shift.template_id.code for shift in shifts}
            return ''.join(by_day.get(date(2026, 9, day), '-') for day in range(7, 13))
        self.assertEqual(pattern(self.employee_a), 'MMNN--')
        self.assertEqual(pattern(self.employee_b), 'MNN--M', 'one day further in the cycle')

    def test_copy_previous(self):
        self.shift(self.morning, day=date(2026, 8, 31))
        self.shift(self.evening, day=date(2026, 9, 1), employee=self.employee_b)
        self.shift(self.night, day=MONDAY)
        resources = (self.employee_a | self.employee_b).resource_id
        count = self.Shift.action_copy_previous('2026-09-07 00:00:00', '2026-09-14 00:00:00', 'week',
                                                [('resource_ids', 'in', resources.ids)])
        self.assertEqual(count, 2)
        copied = self.env['om.planning.slot'].search(
            [('resource_ids', 'in', self.employee_b.resource_id.ids), ('shift_date', '=', date(2026, 9, 8))])
        self.assertEqual((copied.template_id, copied.state), (self.evening, 'draft'))

    def test_roster_gantt(self):
        """ The days of a rostered employee are not greyed until planned, only their time off. """
        self.employee_a._start_rostering(date(2026, 9, 1))
        self.env['resource.calendar.leaves'].create({
            'name': 'Exam', 'resource_id': self.employee_a.resource_id.id, 'shift_unavailability': True,
            'date_from': datetime(2026, 9, 10, 0, 0), 'date_to': datetime(2026, 9, 10, 23, 59)})
        rows = [{'groupedBy': ['resource_ids'], 'resId': employee.resource_id.id}
                for employee in (self.employee_a | self.employee_b)]
        rows = self.Shift.gantt_unavailability('2026-09-07 00:00:00', '2026-09-14 00:00:00', 'week',
                                               ['resource_ids'], rows)
        self.assertEqual([(period['start'].date(), period['stop'].date()) for period in rows[0]['unavailabilities']],
                         [(date(2026, 9, 10), date(2026, 9, 10))])
        self.assertTrue(len(rows[1]['unavailabilities']) > 1, 'not rostered: outside the working schedule')

    def test_claim_open_shift(self):
        open_shift = self.shift(self.morning, employee=self.env['hr.employee'], department_id=self.department.id)
        open_shift.action_publish()
        self.assertEqual(open_shift.department_id, self.department)
        request = self.Request.with_user(self.user_a).create(
            {'request_type': 'claim', 'resource_id': self.employee_a.resource_id.id, 'slot_id': open_shift.id})
        self.assertEqual((request.state, request.approval_state, request.approver_user_ids),
                         ('pending', 'to_approve', self.manager_user))
        self.assertEqual(request.with_user(self.manager_user).can_approve, True)
        request.with_user(self.manager_user).action_approve()
        self.assertEqual((request.state, open_shift.employee_id), ('approved', self.employee_a))
        self.assertEqual(self.work(self.employee_a, MONDAY), [(6.0, 10.0), (10.5, 14.0)])

    def test_swap(self):
        mine = self.shift(self.morning)
        theirs = self.shift(self.evening, day=date(2026, 9, 8), employee=self.employee_b)
        (mine | theirs).action_publish()
        request = self.Request.with_user(self.user_a).create(
            {'resource_id': self.employee_a.resource_id.id, 'slot_id': mine.id, 'target_slot_id': theirs.id})
        self.assertEqual((request.state, request.with_user(self.user_b).can_accept), ('to_accept', True),
                         'the colleague accepts first')
        with self.assertRaises(UserError):
            request.with_user(self.manager_user).action_accept()
        request.with_user(self.user_b).action_accept()
        self.assertEqual((request.state, request.approver_user_ids), ('pending', self.manager_user))
        request.with_user(self.manager_user).action_approval_approve()
        self.assertEqual(request.state, 'approved')
        self.assertEqual((mine.employee_id, theirs.employee_id), (self.employee_b, self.employee_a))
        self.assertEqual(self.work(self.employee_a, date(2026, 9, 8)), [(14.0, 18.0), (18.5, 22.0)])

    def test_swap_declined(self):
        mine = self.shift(self.morning)
        theirs = self.shift(self.evening, day=date(2026, 9, 8), employee=self.employee_b)
        (mine | theirs).action_publish()
        request = self.Request.with_user(self.user_a).create(
            {'resource_id': self.employee_a.resource_id.id, 'slot_id': mine.id, 'target_slot_id': theirs.id})
        request.with_user(self.user_b).action_decline()
        self.assertEqual(request.state, 'refused')
        self.assertEqual((mine.employee_id, theirs.employee_id), (self.employee_a, self.employee_b))

    def test_claim_other_department_refused(self):
        other = self.env['hr.department'].create({'name': 'Elsewhere'})
        open_shift = self.shift(self.morning, employee=self.env['hr.employee'], department_id=other.id)
        open_shift.action_publish()
        with self.assertRaises(UserError):
            self.Request.with_user(self.user_a).create(
                {'request_type': 'claim', 'resource_id': self.employee_a.resource_id.id, 'slot_id': open_shift.id})

    def test_access(self):
        published = self.shift(self.morning)
        published.action_publish()
        draft = self.shift(self.evening, day=date(2026, 9, 8))
        theirs = self.shift(self.morning, employee=self.employee_b)
        theirs.action_publish()
        open_shift = self.shift(self.night, employee=self.env['hr.employee'])
        open_shift.action_publish()
        # among the shifts of the test: the database may hold others, e.g. the open shifts of the demo
        mine = published | draft | theirs | open_shift
        seen = self.env['om.planning.slot'].with_user(self.user_a).search([('id', 'in', mine.ids)])
        self.assertEqual(seen, published | open_shift)
        with self.assertRaises(AccessError):
            draft.with_user(self.user_a).read(['start_datetime'])
        with self.assertRaises(AccessError):
            self.env['om.planning.slot'].with_user(self.user_a).create(
                self.morning._shift_values(date(2026, 9, 9), self.employee_a))

    def test_lateness_against_the_shift(self):
        if 'hr.lateness' not in self.env:
            return
        self.employee_a.lateness_policy_id = self.env.ref('om_hr_lateness.policy_standard')
        self.employee_a._start_rostering(date(2026, 9, 1))
        self.shift(self.evening).action_publish()
        self.env['hr.attendance'].create({'employee_id': self.employee_a.id,
                                          'check_in': datetime(2026, 9, 7, 14, 30),
                                          'check_out': datetime(2026, 9, 7, 22, 0)})
        late = self.env['hr.lateness'].search([('employee_id', '=', self.employee_a.id)])
        self.assertEqual((late.kind, late.minutes), ('late_in', 30), 'late against the 14:00 shift')
