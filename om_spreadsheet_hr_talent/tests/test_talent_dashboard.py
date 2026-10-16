from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestTalentDashboard(HttpCase):

    def test_talent_dashboard(self):
        employee = self.env['hr.employee'].create({'name': 'Dashboard Talent'})
        self.env['hr.appraisal'].create({'employee_id': employee.id})
        self.env['document.document'].create({
            'res_model': 'hr.employee', 'res_id': employee.id,
            'type_id': self.env.ref('om_hr_document.document_type_passport').id,
            'date_expiry': fields.Date.today() + timedelta(days=10)})
        self.start_tour('/odoo/action-spreadsheet_dashboard.ir_actions_dashboard_action', 'om_spreadsheet_hr_talent',
                        login='admin')
