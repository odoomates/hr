from datetime import datetime

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from .fake_device import FakeDevice


@tagged('post_install', '-at_install')
class TestZk(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fake = FakeDevice(password=123456, users=[('301', 'Device Name')], punches=[
            ('301', datetime(2026, 9, 7, 8, 0), 0, 1),
            ('301', datetime(2026, 9, 7, 17, 0), 1, 1),
        ])
        cls.addClassCleanup(cls.fake.close)
        cls.device = cls.env['hr.biometric.device'].create({
            'name': 'TCP Gate', 'protocol': 'zk', 'ip_address': '127.0.0.1', 'port': cls.fake.port,
            'comm_key': '123456', 'timezone': 'UTC', 'zk_timeout': 5})
        cls.employee = cls.env['hr.employee'].create({'name': 'TCP Employee', 'biometric_code': '301'})

    def test_download_and_users(self):
        self.device.action_zk_test()
        self.assertEqual(self.device.serial_number, 'FAKE123')
        self.assertEqual(self.device.device_model, 'FakeFace')

        self.env['hr.biometric.device']._cron_zk_download()
        attendance = self.env['hr.attendance'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual((attendance.check_in, attendance.check_out),
                         (datetime(2026, 9, 7, 8, 0), datetime(2026, 9, 7, 17, 0)))
        self.assertEqual(attendance.in_device_id, self.device)
        self.assertEqual(self.device.zk_last_log_time, datetime(2026, 9, 7, 17, 0))
        self.assertFalse(self.device._zk_download(), 'Downloaded again: nothing new')

        self.device.action_query_users()
        self.assertEqual(self.device.user_ids.employee_id, self.employee)
        other = self.env['hr.employee'].create({'name': 'Sent From Odoo'})
        self.device._push_users(other)
        self.assertIn(other.biometric_code, self.fake.users)
        self.assertEqual(self.fake.disabled, 0, 'The device is always unlocked again')
        self.device.user_ids.filtered(lambda u: u.employee_id == other).action_remove_from_device()
        self.assertNotIn(other.biometric_code, self.fake.users)

        self.device.action_zk_clear_log()
        self.assertTrue(self.fake.cleared)
        self.assertEqual(self.env['hr.biometric.log'].search_count([('device_id', '=', self.device.id)]), 2)

    def test_wrong_key_and_unreachable(self):
        self.device.comm_key = '1'
        with self.assertRaisesRegex(UserError, 'communication key'):
            self.device.action_zk_test()
        self.device.port = 1
        self.env['hr.biometric.device']._cron_zk_download()
        self.assertTrue(self.device.zk_error)
        self.assertEqual(self.device.connection_state, 'offline')

    def test_fingerprints(self):
        self.fake.templates = {'301': {6: b'right-index', 5: b'right-thumb'}}
        self.env.company.biometric_store_templates = True
        self.device.action_query_users()
        user = self.device.user_ids
        self.assertEqual(user.fingerprint_count, 2)
        self.assertEqual(len(user.template_ids), 2)

        other = FakeDevice()
        self.addCleanup(other.close)
        target = self.env['hr.biometric.device'].create({
            'name': 'TCP Gate 2', 'protocol': 'zk', 'ip_address': '127.0.0.1', 'port': other.port,
            'timezone': 'UTC', 'zk_timeout': 5})
        user._copy_to(target)
        self.assertEqual(other.templates, {'301': {6: b'right-index', 5: b'right-thumb'}})
        self.assertEqual(other.users['301'], 'Device Name')
        self.assertEqual(target.user_ids.employee_id, self.employee)
        self.assertEqual(other.disabled, 0)

        target._enroll(target.user_ids, 7)
        self.assertEqual(other.enrolled, [('301', 7)])
