from datetime import datetime

from odoo import fields
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestTimeDashboard(HttpCase):

    def test_time_dashboard(self):
        department = self.env['hr.department'].create({'name': 'Dashboard Time Department'})
        employee = self.env['hr.employee'].create({'name': 'Dashboard Worker', 'department_id': department.id})
        today = fields.Date.context_today(self.env['hr.attendance'])
        attendance = self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': datetime(today.year, today.month, 1, 8, 0),
            'check_out': datetime(today.year, today.month, 1, 12, 0),
        })
        attendance.state = 'validated'
        self.assertEqual(attendance.employee_department_id, department)
        self.start_tour('/odoo/action-spreadsheet_dashboard.ir_actions_dashboard_action', 'om_spreadsheet_hr_time',
                        login='admin')
