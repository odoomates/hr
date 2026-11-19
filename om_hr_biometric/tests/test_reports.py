from datetime import date, datetime, timedelta

from odoo import Command, fields
from odoo.tests import tagged

from .common import BiometricCase


@tagged('post_install', '-at_install')
class TestReports(BiometricCase):

    def test_attendance_status_and_sheet(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'Biometric 8-17', 'attendance_ids': [
                Command.create({'dayofweek': str(day), 'hour_from': hour_from, 'hour_to': hour_to,
                                'day_period': period})
                for day in range(5) for hour_from, hour_to, period in ((8, 12, 'morning'), (13, 17, 'afternoon'))]})
        self.employee.write({'tz': 'UTC', 'resource_calendar_id': calendar.id})
        self.employee.version_id.resource_calendar_id = calendar
        self.env['resource.calendar.leaves'].create({
            'name': 'Public holiday', 'calendar_id': calendar.id,
            'date_from': datetime(2026, 9, 11, 0, 0), 'date_to': datetime(2026, 9, 11, 23, 59)})
        attend = [(7, 8, 0, 17, 0), (8, 8, 20, 17, 0), (10, 8, 0, None, None), (12, 9, 0, 12, 0)]
        for day, in_hour, in_minute, out_hour, out_minute in attend:
            self.env['hr.attendance'].create({
                'employee_id': self.employee.id, 'check_in': datetime(2026, 9, day, in_hour, in_minute),
                'check_out': out_hour and datetime(2026, 9, day, out_hour, out_minute)})
        wizard = self.env['hr.biometric.status.wizard'].create({
            'date_from': date(2026, 9, 7), 'date_to': date(2026, 9, 13), 'tolerance': 5,
            'employee_ids': [Command.set(self.employee.ids)]})
        lines = wizard._compute_lines()
        self.assertEqual({line.date.day: line.status for line in lines}, {
            7: 'on_time', 8: 'late', 9: 'absent', 10: 'missing_out', 11: 'leave', 12: 'day_off_worked'})
        self.assertAlmostEqual(lines.filtered(lambda line: line.date.day == 8).late_minutes, 20)
        dates, rows = wizard._sheet()
        self.assertEqual(len(dates), 7)
        self.assertEqual(rows[0][1], ['✓', 'L', 'A', 'M', 'T', 'X', ''])
        self.assertEqual(rows[0][2]['absent'], 1)
        html = self.env['ir.actions.report']._render_qweb_html('om_hr_biometric.report_monthly_sheet', wizard.ids)[0]
        self.assertIn(b'Punch Employee', html)

    def test_offline_alert(self):
        self.device.write({'responsible_id': self.env.user.id,
                           'last_contact': fields.Datetime.now() - timedelta(hours=2)})
        self.env['hr.biometric.device']._cron_check_offline()
        self.env['hr.biometric.device']._cron_check_offline()
        activity = self.device._offline_activities()
        self.assertEqual(len(activity), 1, 'One activity per outage')
        self.assertEqual(activity.user_id, self.env.user)
        self.device._touch()
        self.assertFalse(self.device._offline_activities())

    def test_users_matched_by_name(self):
        garcia = self.env['hr.employee'].create({'name': 'José García'})
        self.env['hr.employee'].create({'name': 'Anna Smith'})
        self.env['hr.employee'].create({'name': 'Anna Smithson'})
        Users = self.env['hr.biometric.device.user']
        accents = Users.create({'device_id': self.device.id, 'user_code': '501', 'name': 'jose garcia'})
        self.assertEqual(accents.employee_id, garcia)
        self.assertEqual(garcia.biometric_code, '501')
        ambiguous = Users.create({'device_id': self.device.id, 'user_code': '502', 'name': 'Anna Smi'})
        self.assertFalse(ambiguous.employee_id, 'A name shared by several employees is left to link by hand')
        exact = Users.create({'device_id': self.device.id, 'user_code': '503', 'name': 'Anna Smith'})
        self.assertEqual(exact.employee_id.name, 'Anna Smith')

    def test_old_commands_deleted(self):
        Command_ = self.env['hr.biometric.command']
        old = Command_.create({'device_id': self.device.id, 'command': 'reboot', 'payload': 'REBOOT', 'state': 'done'})
        recent = Command_.create({'device_id': self.device.id, 'command': 'reboot', 'payload': 'REBOOT',
                                  'state': 'done'})
        pending = Command_.create({'device_id': self.device.id, 'command': 'reboot', 'payload': 'REBOOT'})
        self.env.cr.execute("UPDATE hr_biometric_command SET create_date = NOW() - INTERVAL '200 days' "
                            "WHERE id IN %s", [(old.id, pending.id)])
        Command_.invalidate_model(['create_date'])
        Command_._cron_cleanup()
        self.assertFalse(old.exists())
        self.assertTrue(recent.exists())
        self.assertTrue(pending.exists(), 'A pending command is kept')
