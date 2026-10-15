from datetime import date

from odoo import Command, fields
from odoo.tests import Form, HttpCase, tagged


@tagged('post_install', '-at_install')
class TestPayrollDashboard(HttpCase):

    def test_payroll_dashboard(self):
        today = fields.Date.context_today(self.env['hr.payslip'])
        rules = self.env.ref('om_hr_payroll.hr_rule_basic') | self.env.ref('om_hr_payroll.hr_rule_taxable') \
            | self.env.ref('om_hr_payroll.hr_rule_net')
        structure = self.env['hr.payroll.structure'].create({
            'name': 'Dashboard Structure', 'code': 'DASHTEST', 'parent_id': False, 'rule_ids': [Command.set(rules.ids)]})
        employee = self.env['hr.employee'].create({
            'name': 'Dashboard Payee', 'date_version': date(today.year, 1, 1),
            'contract_date_start': date(today.year, 1, 1), 'wage': 5000.0, 'struct_id': structure.id})
        with Form(self.env['hr.payslip']) as form:
            form.employee_id = employee
            form.date_from = date(today.year, today.month, 1)
            form.date_to = today
        payslip = form.record
        payslip.compute_sheet()
        payslip.write({'state': 'done'})
        self.start_tour('/odoo/action-spreadsheet_dashboard.ir_actions_dashboard_action', 'om_spreadsheet_hr_payroll',
                        login='admin')
