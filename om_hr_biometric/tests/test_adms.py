from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestAdms(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.device = cls.env['hr.biometric.device'].create({
            'name': 'ADMS Gate', 'serial_number': 'OMBIO-ADMS-1', 'timezone': 'UTC'})
        cls.employee = cls.env['hr.employee'].create({'name': 'ADMS Employee', 'biometric_code': '201'})

    def test_punches_and_commands(self):
        response = self.url_open('/iclock/cdata?SN=OMBIO-ADMS-1&options=all&pushver=2.4.1')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.text.startswith('GET OPTION FROM: OMBIO-ADMS-1'))
        self.assertTrue(self.device.last_contact)

        body = '201\t2026-09-07 08:00:00\t0\t1\t0\t0\t0\n201\t2026-09-07 17:00:00\t1\t1\t0\t0\t0\n'
        for _i in range(2):  # sent twice: received once
            response = self.url_open('/iclock/cdata?SN=OMBIO-ADMS-1&table=ATTLOG&Stamp=100', data=body)
            self.assertEqual(response.text, 'OK:2')
        attendance = self.env['hr.attendance'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual(len(attendance), 1)
        self.assertEqual((attendance.in_mode, attendance.out_mode), ('biometric', 'biometric'))
        self.assertEqual(self.device.attlog_stamp, '100')

        self.device._push_users(self.employee)
        command = self.env['hr.biometric.command'].search([('device_id', '=', self.device.id)])
        response = self.url_open('/iclock/getrequest?SN=OMBIO-ADMS-1')
        self.assertEqual(response.text, 'C:%d:DATA UPDATE USERINFO PIN=201\tName=ADMS Employee\tPri=0\n'
                         % command.id)
        self.assertEqual(command.state, 'sent')
        self.url_open('/iclock/devicecmd?SN=OMBIO-ADMS-1', data='ID=%d&Return=0&CMD=DATA\n' % command.id)
        self.assertEqual(command.state, 'done')
        self.assertEqual(command.device_user_id.state, 'on_device')

    def test_unknown_device_refused(self):
        self.assertEqual(self.url_open('/iclock/cdata?SN=UNKNOWN').status_code, 403)
        self.device.allowed_ips = '203.0.113.7'
        self.assertEqual(self.url_open('/iclock/getrequest?SN=OMBIO-ADMS-1').status_code, 403)

    def test_fingerprints(self):
        body = ('USER PIN=201\tName=Ann\tPri=0\n'
                'FP PIN=201\tFID=6\tSize=8\tValid=1\tTMP=QUJDRA==\n'
                'FP PIN=201\tFID=5\tSize=8\tValid=1\tTMP=RUZHSA==\n')
        self.url_open('/iclock/cdata?SN=OMBIO-ADMS-1&table=OPERLOG', data=body)
        user = self.device.user_ids
        self.assertEqual((user.employee_id, user.fingerprint_count), (self.employee, 2))
        self.assertFalse(user.template_ids, 'Not kept unless the company chooses to')
        with self.assertRaises(UserError):
            user._copy_to(self.device)

        self.env.company.biometric_store_templates = True
        self.url_open('/iclock/cdata?SN=OMBIO-ADMS-1&table=OPERLOG', data=body)
        self.assertEqual(sorted(user.template_ids.mapped('index')), [5, 6])
        target = self.env['hr.biometric.device'].create({
            'name': 'ADMS Gate 2', 'serial_number': 'OMBIO-ADMS-2', 'timezone': 'UTC'})
        user._copy_to(target)
        commands = self.env['hr.biometric.command'].search([('device_id', '=', target.id)], order='id')
        self.assertEqual(commands.mapped('command'), ['user_update', 'template_update', 'template_update'])
        self.assertIn('DATA UPDATE FINGERTMP PIN=201\tFID=', commands[1].payload)

        target._enroll(target.user_ids, 3)
        self.assertEqual(self.env['hr.biometric.command'].search([('device_id', '=', target.id)], limit=1).payload,
                         'ENROLL_FP PIN=201\tFID=3\tRETRY=3\tOVERWRITE=1')
