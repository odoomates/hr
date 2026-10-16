from datetime import UTC, date, datetime, time, timedelta

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged

from odoo.addons.om_hr_shift.models.hr_shift_template import shift_segments

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
        cls.Shift = cls.env['hr.shift'].with_user(cls.planner)

    def shift(self, template, day=MONDAY, employee=None, **values):
        employee = self.employee_a if employee is None else employee
        return self.Shift.create(dict(template._shift_values(), employee_id=employee.id or False, date=day, **values))

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
        self.assertEqual(shift_segments(6, 14, 10, 10.5), [(0, 6, 10), (0, 10.5, 14)])
        self.assertEqual(shift_segments(22, 6, 2, 2.5), [(0, 22, 24), (1, 0, 2), (1, 2.5, 6)])
        self.assertEqual(shift_segments(22, 6), [(0, 22, 24), (1, 0, 6)])
        self.assertEqual((self.morning.hours, self.night.hours), (7.5, 7.5))

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
        self.assertEqual(len(shift.attendance_ids), 2)
        shift.write({'hour_to': 15})
        self.assertEqual(self.work(self.employee_a, MONDAY), [(6.0, 10.0), (10.5, 15.0)], 'an edit follows')
        shift.employee_id = self.employee_b
        self.assertEqual(self.work(self.employee_a, MONDAY), [])
        self.assertTrue(self.employee_b.roster_calendar_id, 'rostered when given a published shift')
        self.assertEqual(self.work(self.employee_b, MONDAY), [(6.0, 10.0), (10.5, 15.0)])
        shift.unlink()
        self.assertEqual(self.work(self.employee_b, MONDAY), [])

    def test_night_shift(self):
        self.employee_a._start_rostering(date(2026, 9, 1))
        self.shift(self.night).action_publish()
        self.assertEqual(self.work(self.employee_a, MONDAY), [(22.0, 24.0)])
        self.assertEqual(self.work(self.employee_a, date(2026, 9, 8)), [(0.0, 2.0), (2.5, 6.0)])

    def test_checks_and_override(self):
        self.employee_a._start_rostering(date(2026, 9, 1))
        self.env['resource.calendar.leaves'].create({
            'name': 'Holiday Trip', 'resource_id': self.employee_a.resource_id.id,
            'date_from': datetime(2026, 9, 9, 0, 0), 'date_to': datetime(2026, 9, 9, 23, 59)})
        self.env['hr.shift.unavailability'].create({'employee_id': self.employee_a.id, 'date_from': date(2026, 9, 10),
                                                       'date_to': date(2026, 9, 10), 'reason': 'Exam'})
        evening = self.shift(self.evening)
        morning = self.shift(self.morning, day=date(2026, 9, 8))
        trip = self.shift(self.morning, day=date(2026, 9, 9))
        exam = self.shift(self.morning, day=date(2026, 9, 10))
        overlap = self.shift(self.morning, day=date(2026, 9, 10))
        self.assertFalse(self.shift(self.morning, day=date(2026, 9, 14), employee=self.employee_b).warning)
        self.assertIn('rest', evening.warning)
        self.assertIn('rest', morning.warning, '8 hours between 22:00 and 06:00')
        self.assertIn('Holiday Trip', trip.warning)
        self.assertIn('Exam', exam.warning)
        self.assertIn('Overlaps', overlap.warning)
        self.employee_a.company_id.shift_max_week_hours = 20
        exam.invalidate_recordset(['warning'])
        self.assertIn('hours in the week', exam.warning)
        action = trip.action_publish()
        self.assertEqual(action['res_model'], 'hr.shift.publish.wizard')
        self.assertEqual(trip.state, 'draft', 'not without the planner confirming')
        wizard = self.env['hr.shift.publish.wizard'].with_user(self.planner).create(
            {'shift_ids': [Command.set(trip.ids)], 'reason': 'Trip moved'})
        self.assertIn('Holiday Trip', wizard.warnings)
        wizard.action_publish()
        self.assertEqual(trip.state, 'published')
        self.assertIn('Trip moved', trip.message_ids[0].body)

    def test_rotation(self):
        rotation = self.env.ref('om_hr_shift.rotation_two_two_two')
        self.assertEqual(rotation.pattern, 'M M N N - -')
        wizard = self.env['hr.shift.rotation.wizard'].with_user(self.planner).create({
            'rotation_id': rotation.id, 'employee_ids': [Command.set((self.employee_a | self.employee_b).ids)],
            'date_from': MONDAY, 'date_to': date(2026, 9, 12), 'stagger': True})
        wizard.action_apply()

        def pattern(employee):
            shifts = self.env['hr.shift'].search([('employee_id', '=', employee.id)])
            by_day = {shift.date: shift.template_id.code for shift in shifts}
            return ''.join(by_day.get(date(2026, 9, day), '-') for day in range(7, 13))
        self.assertEqual(pattern(self.employee_a), 'MMNN--')
        self.assertEqual(pattern(self.employee_b), 'MNN--M', 'one day further in the cycle')

    def test_copy_previous(self):
        self.shift(self.morning, day=date(2026, 8, 31))
        self.shift(self.evening, day=date(2026, 9, 1), employee=self.employee_b)
        self.shift(self.night, day=MONDAY)
        count = self.Shift.roster_copy_previous(MONDAY, 7)
        self.assertEqual(count, 1, 'the employee planned on that day already is left as is')
        copied = self.env['hr.shift'].search(
            [('employee_id', '=', self.employee_b.id), ('date', '=', date(2026, 9, 8))])
        self.assertEqual((copied.template_id, copied.state), (self.evening, 'draft'))

    def test_roster_data(self):
        self.employee_a._start_rostering(date(2026, 9, 1))
        self.shift(self.morning)
        self.shift(self.night, employee=self.env['hr.employee'], department_id=self.department.id)
        data = self.Shift.roster_data('2026-09-07', 7, self.department.id)
        self.assertEqual(len(data['dates']), 7)
        self.assertIn(self.employee_a.id, [employee['id'] for employee in data['employees']])
        self.assertEqual({shift['employee_id'] for shift in data['shifts']}, {self.employee_a.id, False})
        self.assertTrue(data['can_edit'])
        self.assertFalse(self.env['hr.shift'].with_user(self.user_a).roster_data('2026-09-07', 7)['can_edit'])

    def test_claim_open_shift(self):
        open_shift = self.shift(self.morning, employee=self.env['hr.employee'], department_id=self.department.id)
        open_shift.action_publish()
        request = self.env['hr.shift.request'].with_user(self.user_a).create(
            {'kind': 'claim', 'employee_id': self.employee_a.id, 'shift_id': open_shift.id})
        request.action_submit()
        self.assertEqual((request.state, request.approver_user_ids), ('to_approve', self.manager_user))
        request.with_user(self.manager_user).action_approval_approve()
        self.assertEqual((request.state, open_shift.employee_id), ('approved', self.employee_a))
        self.assertEqual(self.work(self.employee_a, MONDAY), [(6.0, 10.0), (10.5, 14.0)])

    def test_swap(self):
        mine = self.shift(self.morning)
        theirs = self.shift(self.evening, day=date(2026, 9, 8), employee=self.employee_b)
        (mine | theirs).action_publish()
        request = self.env['hr.shift.request'].with_user(self.user_a).create(
            {'kind': 'swap', 'employee_id': self.employee_a.id, 'shift_id': mine.id, 'target_shift_id': theirs.id})
        request.action_submit()
        self.assertEqual((request.state, request.with_user(self.user_b).can_accept), ('to_accept', True),
                         'the colleague accepts first')
        with self.assertRaises(UserError):
            request.with_user(self.manager_user).action_accept()
        request.with_user(self.user_b).action_accept()
        self.assertEqual((request.state, request.approver_user_ids), ('to_approve', self.manager_user))
        request.with_user(self.manager_user).action_approval_approve()
        self.assertEqual((mine.employee_id, theirs.employee_id), (self.employee_b, self.employee_a))
        self.assertEqual(self.work(self.employee_a, date(2026, 9, 8)), [(14.0, 18.0), (18.5, 22.0)])

    def test_swap_declined(self):
        mine = self.shift(self.morning)
        theirs = self.shift(self.evening, day=date(2026, 9, 8), employee=self.employee_b)
        (mine | theirs).action_publish()
        request = self.env['hr.shift.request'].with_user(self.user_a).create(
            {'kind': 'swap', 'employee_id': self.employee_a.id, 'shift_id': mine.id, 'target_shift_id': theirs.id})
        request.action_submit()
        request.with_user(self.user_b).action_decline()
        self.assertEqual(request.state, 'refused')
        self.assertEqual((mine.employee_id, theirs.employee_id), (self.employee_a, self.employee_b))

    def test_claim_other_department_refused(self):
        other = self.env['hr.department'].create({'name': 'Elsewhere'})
        open_shift = self.shift(self.morning, employee=self.env['hr.employee'], department_id=other.id)
        open_shift.action_publish()
        request = self.env['hr.shift.request'].with_user(self.user_a).create(
            {'kind': 'claim', 'employee_id': self.employee_a.id, 'shift_id': open_shift.id})
        with self.assertRaises(UserError):
            request.action_submit()

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
        seen = self.env['hr.shift'].with_user(self.user_a).search([('id', 'in', mine.ids)])
        self.assertEqual(seen, published | open_shift)
        with self.assertRaises(AccessError):
            draft.with_user(self.user_a).read(['date'])
        with self.assertRaises((AccessError, UserError)):
            self.env['hr.shift'].with_user(self.user_a).roster_assign(self.employee_a.id, '2026-09-09',
                                                                             self.morning.id)

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


@tagged('post_install', '-at_install')
class TestRosterBoard(HttpCase):

    def test_roster_board(self):
        monday = date.today() - timedelta(days=date.today().weekday())
        employee = self.env['hr.employee'].create({'name': 'Roster Tour', 'tz': 'UTC',
                                                   'date_version': monday - timedelta(days=30),
                                                   'contract_date_start': monday - timedelta(days=30)})
        employee._start_rostering(monday)
        # nothing to warn of: the tour publishes straight away
        employee.company_id.write({'shift_min_rest': 0, 'shift_max_week_hours': 0})
        self.env['resource.calendar.leaves'].search([
            ('date_from', '<', datetime.combine(monday + timedelta(days=1), time.min)),
            ('date_to', '>', datetime.combine(monday, time.min))]).unlink()
        self.start_tour('/odoo/action-om_hr_shift.om_hr_shift_action_roster', 'om_hr_shift_roster', login='admin')
        shift = self.env['hr.shift'].search([('employee_id', '=', employee.id)])
        self.assertEqual((shift.date, shift.state, len(shift.attendance_ids)), (monday, 'published', 2))
