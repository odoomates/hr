from datetime import datetime

from odoo.tests import TransactionCase


class BiometricCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.biometric_max_shift = 16
        cls.device = cls.env['hr.biometric.device'].create({
            'name': 'Gate', 'serial_number': 'OMBIO-TEST-1', 'timezone': 'UTC', 'company_id': cls.company.id})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Punch Employee', 'biometric_code': '101', 'company_id': cls.company.id})

    def punch(self, when, code='101', status='', device=None):
        """ Punch `when` (naive, time of the device) and process. :return: the punch """
        logs = self.env['hr.biometric.log']._create_punches(device or self.device, [{
            'user_code': code, 'local_time': when, 'status': status}], 'import')
        logs._process()
        return logs

    def attendances(self, employee=None):
        return self.env['hr.attendance'].search([('employee_id', '=', (employee or self.employee).id)],
                                                order='check_in')

    @staticmethod
    def at(day, hour, minute=0, second=0):
        return datetime(2026, 9, day, hour, minute, second)
