from datetime import datetime

from odoo import Command
from odoo.tests import tagged

from odoo.addons.om_hr_biometric.tests.common import BiometricCase


@tagged('post_install', '-at_install')
class TestBiometricShift(BiometricCase):

    def shift(self, day, hour_from, hour_to):
        return self.env['om.planning.slot'].create({
            'resource_ids': [Command.set(self.employee.resource_id.ids)],
            'start_datetime': datetime(2026, 9, day, hour_from), 'end_datetime': datetime(2026, 9, day, hour_to),
            'break_hours': 0.0, 'state': 'published'})

    def test_missed_check_in(self):
        """ Without shifts, a missed check-in turns the next days around; with them, it stays a missed check-in. """
        self.employee.tz = 'UTC'
        self.shift(7, 8, 17)
        self.shift(8, 8, 17)
        missed = self.punch(self.at(7, 17))
        self.assertEqual((missed.state, missed.punch), ('error', False))
        self.punch(self.at(8, 8))
        self.punch(self.at(8, 17))
        attendance = self.attendances()
        self.assertEqual((attendance.check_in, attendance.check_out), (self.at(8, 8), self.at(8, 17)))

    def test_missed_check_out(self):
        """ A check-in of the night before is closed when the next shift starts, well within the maximum shift. """
        self.employee.tz = 'UTC'
        self.shift(7, 14, 22)
        self.shift(8, 6, 14)
        self.punch(self.at(7, 14))
        self.punch(self.at(8, 6))
        first, second = self.attendances()
        self.assertTrue(first.biometric_review)
        self.assertEqual(second.check_in, self.at(8, 6))
        self.assertFalse(second.check_out)
