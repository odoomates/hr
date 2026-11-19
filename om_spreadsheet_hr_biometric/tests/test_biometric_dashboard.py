from datetime import datetime

from odoo import fields
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestBiometricDashboard(HttpCase):

    def test_biometric_dashboard(self):
        device = self.env['hr.biometric.device'].create({
            'name': 'Dashboard Gate', 'serial_number': 'OMBIO-DASH-1', 'timezone': 'UTC'})
        self.env['hr.employee'].create({'name': 'Dashboard Puncher', 'biometric_code': '901'})
        today = fields.Date.context_today(device)
        self.env['hr.biometric.log']._create_punches(device, [
            {'user_code': '901', 'local_time': datetime(today.year, today.month, 1, 8, 0)}], 'import')._process()
        self.start_tour('/odoo/action-spreadsheet_dashboard.ir_actions_dashboard_action',
                        'om_spreadsheet_hr_biometric', login='admin')
