from datetime import date, datetime

from odoo.tests import tagged

from .common import BiometricCase


@tagged('post_install', '-at_install')
class TestProcessing(BiometricCase):

    def test_alternate(self):
        for hour in (8, 12, 13, 17):
            log = self.punch(self.at(7, hour))
            self.assertEqual(log.state, 'done')
        attendances = self.attendances()
        self.assertEqual(len(attendances), 2)
        self.assertEqual((attendances[0].check_in, attendances[0].check_out), (self.at(7, 8), self.at(7, 12)))
        self.assertEqual((attendances[1].check_in, attendances[1].check_out), (self.at(7, 13), self.at(7, 17)))
        self.assertEqual(attendances[0].out_device_id, self.device)
        self.assertEqual(attendances[0].in_device_id, self.device)

    def test_status_255_alternates(self):
        """ A punch without a known status (255) is never forced to a check-in. """
        self.device.attendance_mode = 'status_code'
        self.punch(self.at(7, 8), status='255')
        self.punch(self.at(7, 17), status='255')
        attendance = self.attendances()
        self.assertEqual((attendance.check_in, attendance.check_out), (self.at(7, 8), self.at(7, 17)))

    def test_forgotten_check_out(self):
        """ One forgotten check-out never blocks the next days. """
        self.punch(self.at(7, 8))
        self.punch(self.at(8, 8))
        self.punch(self.at(8, 17))
        first, second = self.attendances()
        self.assertEqual(first.check_out, first.check_in)
        self.assertTrue(first.biometric_review)
        self.assertEqual((second.check_in, second.check_out), (self.at(8, 8), self.at(8, 17)))
        self.assertFalse(second.biometric_review)

    def test_late_punch_and_reprocess(self):
        self.punch(self.at(8, 8))
        self.punch(self.at(8, 17))
        late = self.punch(self.at(7, 8))
        self.assertEqual(late.state, 'error')
        self.punch(self.at(7, 17))
        self.env['hr.biometric.log']._reprocess(date(2026, 9, 7), date(2026, 9, 8))
        attendances = self.attendances()
        self.assertEqual([(a.check_in, a.check_out) for a in attendances],
                         [(self.at(7, 8), self.at(7, 17)), (self.at(8, 8), self.at(8, 17))])
        self.assertEqual(set(self.env['hr.biometric.log'].search([('device_id', '=', self.device.id)])
                             .mapped('state')), {'done'})

    def test_unknown_user_then_linked(self):
        log = self.punch(self.at(7, 8), code='999')
        self.assertEqual(log.state, 'unmapped')
        other = self.env['hr.employee'].create({'name': 'Late Comer'})
        other.biometric_code = '999'
        self.assertEqual(log.state, 'done')
        self.assertEqual(log.employee_id, other)
        self.assertEqual(self.attendances(other).check_in, self.at(7, 8))

    def test_device_timezone_and_dst(self):
        self.device.timezone = 'Europe/Brussels'
        log = self.punch(datetime(2026, 7, 1, 8, 0))
        self.assertEqual(log.timestamp, datetime(2026, 7, 1, 6, 0))
        self.assertEqual(log.local_time, '2026-07-01 08:00:00')
        # 02:30 happens twice on 25 October 2026: the first one, still in summer time
        log = self.punch(datetime(2026, 10, 25, 2, 30))
        self.assertEqual(log.timestamp, datetime(2026, 10, 25, 0, 30))
        # 02:30 does not exist on 29 March 2026: no crash
        log = self.punch(datetime(2026, 3, 29, 2, 30))
        self.assertTrue(log.timestamp)
