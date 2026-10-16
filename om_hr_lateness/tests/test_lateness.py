from datetime import date, datetime

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged

MONDAY = date(2026, 9, 7)


@tagged('post_install', '-at_install')
class TestLateness(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.officer = new_test_user(cls.env, 'om_late_officer',
                                    groups='base.group_user,hr_attendance.group_hr_attendance_officer')
        cls.other_officer = new_test_user(cls.env, 'om_late_other_officer',
                                          groups='base.group_user,hr_attendance.group_hr_attendance_officer')
        cls.employee_user = new_test_user(cls.env, 'om_late_employee', groups='base.group_user')
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Late 8-17', 'attendance_ids': [
                Command.create({'dayofweek': str(day), 'hour_from': 8, 'hour_to': 12,
                                'day_period': 'morning'}) for day in range(5)] + [
                Command.create({'dayofweek': str(day), 'hour_from': 13, 'hour_to': 17,
                                'day_period': 'afternoon'}) for day in range(5)]})
        cls.policy = cls.env['hr.lateness.policy'].create({
            'name': 'Test Policy', 'grace_in': 10, 'grace_out': 10, 'line_ids': [
                Command.create({'minutes_from': 0, 'minutes_to': 30, 'occurrence': 1, 'penalty': 'warning'}),
                Command.create({'minutes_from': 0, 'minutes_to': 30, 'occurrence': 2, 'penalty': 'fixed',
                                'amount': 50}),
                Command.create({'minutes_from': 0, 'minutes_to': 30, 'occurrence': 3, 'penalty': 'daily_percent',
                                'percent': 10}),
                Command.create({'minutes_from': 31, 'occurrence': 1, 'penalty': 'minutes', 'factor': 1.5}),
            ]})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Late Employee', 'tz': 'UTC', 'user_id': cls.employee_user.id,
            'resource_calendar_id': cls.calendar.id, 'lateness_policy_id': cls.policy.id,
            'attendance_manager_id': cls.officer.id,
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1)})
        cls.employee.version_id.resource_calendar_id = cls.calendar

    def attend(self, day, check_in, check_out=None, employee=None):
        return self.env['hr.attendance'].create({
            'employee_id': (employee or self.employee).id,
            'check_in': datetime.combine(day, datetime.min.time()).replace(hour=int(check_in),
                                                                           minute=round(check_in % 1 * 60)),
            'check_out': check_out and datetime.combine(day, datetime.min.time()).replace(
                hour=int(check_out), minute=round(check_out % 1 * 60)),
        })

    def lateness(self, employee=None):
        return self.env['hr.lateness'].search([('employee_id', '=', (employee or self.employee).id)],
                                                 order='date, kind')

    def test_within_grace(self):
        self.attend(MONDAY, 8 + 5 / 60, 17 - 5 / 60)
        self.assertFalse(self.lateness())

    def test_late_and_early(self):
        attendance = self.attend(MONDAY, 8.5)
        late = self.lateness()
        self.assertEqual((late.kind, late.minutes, late.attendance_id), ('late_in', 30, attendance))
        self.assertEqual(late.scheduled_at, datetime(2026, 9, 7, 8, 0))
        attendance.check_out = datetime(2026, 9, 7, 16, 30)
        self.assertEqual(set(self.lateness().mapped('kind')), {'early_out', 'late_in'})
        attendance.write({'check_in': datetime(2026, 9, 7, 8, 0), 'check_out': datetime(2026, 9, 7, 17, 0)})
        self.assertFalse(self.lateness(), 'corrected: gone')

    def test_lunch_split_counts_the_day(self):
        self.attend(MONDAY, 8, 12)
        self.attend(MONDAY, 13.5, 17)
        self.assertFalse(self.lateness(), 'only the start and the end of the day count')

    def test_time_off_and_holidays(self):
        self.env['resource.calendar.leaves'].create({
            'name': 'Morning off', 'resource_id': self.employee.resource_id.id, 'calendar_id': self.calendar.id,
            'date_from': datetime(2026, 9, 7, 8, 0), 'date_to': datetime(2026, 9, 7, 12, 0)})
        self.env['resource.calendar.leaves'].create({
            'name': 'Holiday', 'calendar_id': self.calendar.id,
            'date_from': datetime(2026, 9, 8, 0, 0), 'date_to': datetime(2026, 9, 8, 23, 59)})
        self.attend(MONDAY, 13, 17)
        self.attend(date(2026, 9, 8), 11, 15)
        self.assertFalse(self.lateness(), 'the afternoon after a morning off, and a holiday, are not late')
        self.attend(date(2026, 9, 9), 9, 17)
        self.assertEqual(self.lateness().date, date(2026, 9, 9))

    def test_night_shift(self):
        night = self.env['resource.calendar'].create({
            'name': 'Nights', 'attendance_ids': [
                Command.create({'dayofweek': '0', 'hour_from': 22, 'hour_to': 24}),
                Command.create({'dayofweek': '1', 'hour_from': 0, 'hour_to': 6})]})
        self.employee.version_id.resource_calendar_id = night
        self.employee.resource_calendar_id = night
        self.env['hr.attendance'].create({'employee_id': self.employee.id, 'check_in': datetime(2026, 9, 7, 22, 0),
                                          'check_out': datetime(2026, 9, 8, 5, 0)})
        early = self.lateness()
        self.assertEqual((early.kind, early.minutes, early.scheduled_at),
                         ('early_out', 60, datetime(2026, 9, 8, 6, 0)), 'the night ends the next morning')

    def test_matrix_and_excuse(self):
        for index, day in enumerate((7, 8, 9, 10)):
            self.attend(date(2026, 9, day), 8.25 if index < 3 else 9, 17)
        late = self.lateness()
        self.assertEqual(late.mapped('occurrence'), [1, 2, 3, 4])
        self.assertEqual(late.mapped('penalty'), ['warning', 'fixed', 'daily_percent', 'minutes'])
        self.assertTrue(late[0].warned)
        self.assertIn(self.employee_user.partner_id, self.employee.message_ids[0].partner_ids)
        late[1].with_user(self.officer)._excuse('Errand for the company')
        self.assertEqual(late.mapped('occurrence'), [1, 0, 2, 3])
        self.assertEqual(late[2].penalty, 'fixed', 'the third is now the second')
        late[1].with_user(self.officer).action_count_again()
        self.assertEqual(late.mapped('occurrence'), [1, 2, 3, 4])
        self.attend(date(2026, 10, 1), 8.25, 17)
        self.assertEqual(self.lateness()[-1].occurrence, 1, 'a new month starts again')

    def test_policy_line_lookup(self):
        line = self.policy._line_for
        self.assertEqual(line('late_in', 20, 5).penalty, 'daily_percent', 'the 3rd and after')
        self.assertEqual(line('late_in', 45, 2).penalty, 'minutes')
        self.assertFalse(self.env['hr.lateness.policy'].create({'name': 'Empty'})._line_for('late_in', 20, 1))

    def test_flexible_skipped(self):
        flexible = self.env['resource.calendar'].create({'name': 'Flexible', 'calendar_type': 'undefined'})
        self.employee.version_id.resource_calendar_id = flexible
        self.employee.resource_calendar_id = flexible
        self.attend(MONDAY, 11, 14)
        self.assertFalse(self.lateness())

    def test_company_policy(self):
        other = self.env['hr.employee'].create({
            'name': 'Company Policy', 'tz': 'UTC', 'resource_calendar_id': self.calendar.id,
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1)})
        other.version_id.resource_calendar_id = self.calendar
        other.company_id.lateness_policy_id = self.env.ref('om_hr_lateness.policy_standard')
        self.attend(MONDAY, 8.5, 17, employee=other)
        late = self.lateness(other)
        self.assertEqual((late.policy_id, late.penalty), (self.env.ref('om_hr_lateness.policy_standard'), 'minutes'))

    def test_access(self):
        self.attend(MONDAY, 8.5, 17)
        other = self.env['hr.employee'].create({'name': 'Someone', 'tz': 'UTC', 'resource_calendar_id': self.calendar.id,
                                                'lateness_policy_id': self.policy.id})
        self.attend(MONDAY, 8.5, 17, employee=other)
        self.assertEqual(self.env['hr.lateness'].with_user(self.employee_user).search([]).employee_id,
                         self.employee, 'an employee sees their own')
        late = self.lateness()
        with self.assertRaises((UserError, AccessError)):
            late.with_user(self.other_officer)._excuse('Not my employee')
        with self.assertRaises((UserError, AccessError)):
            late.with_user(self.employee_user)._excuse('Myself')
        with self.assertRaises(UserError):
            late.with_user(self.officer)._excuse('')

    def test_team_officer_reaches_the_menu(self):
        """ An officer managing only their team, not all the attendances, finds the lateness of their team. """
        visible = self.env['ir.ui.menu'].with_user(self.officer)._visible_menu_ids()
        self.assertFalse(self.officer.has_group('hr_attendance.group_hr_attendance_user'))
        self.assertIn(self.env.ref('om_hr_lateness.menu_om_hr_lateness').id, visible)
