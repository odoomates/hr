from datetime import date, datetime

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestOvertimePayrollMultiCompany(TransactionCase):
    """ Two companies sharing the overtime rule: each payslip pays the overtime of its own employees, at the days
        per month of its own company. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env['res.company'].create({'name': 'Overtime Company B'})
        if 'journal_id' in cls.env['hr.payslip']._fields:
            cls.env['account.journal'].create({
                'name': 'Salaries B', 'code': 'SALOB', 'type': 'general', 'company_id': cls.company_b.id})
        cls.env.company.om_payroll_month_days = 30
        cls.company_b.om_payroll_month_days = 20
        rules = cls.env.ref('om_hr_payroll.hr_rule_basic') \
            | cls.env.ref('om_hr_overtime_payroll.hr_rule_overtime') | cls.env.ref('om_hr_payroll.hr_rule_net')
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Shared Overtime', 'code': 'OTMC', 'parent_id': False, 'company_id': False,
            'rule_ids': [Command.set(rules.ids)]})
        cls.overtime_type = cls.env['hr.work.entry.type'].create({
            'name': 'Shared Overtime', 'code': 'MCOT', 'amount_rate': 1.5})
        # the time rules give the overtime types: an attendance of this type is overtime
        cls.env['hr.time.rule'].create({'name': 'Shared Overtime Rule', 'work_entry_type_id': cls.overtime_type.id})
        cls.employee_a = cls.new_employee(cls.env.company, 'Overtime A')
        cls.employee_b = cls.new_employee(cls.company_b, 'Overtime B')

    @classmethod
    def new_employee(cls, company, name):
        calendar = cls.env['resource.calendar'].create({'name': '40h %s' % name, 'company_id': company.id})
        return cls.env['hr.employee'].with_company(company).create({
            'name': name, 'company_id': company.id, 'tz': 'UTC', 'resource_calendar_id': calendar.id,
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1), 'wage': 3000.0,
            'struct_id': cls.structure.id})

    def overtime(self, employee):
        attendance = self.env['hr.attendance'].with_context(skip_time_rules=True).create({
            'employee_id': employee.id, 'check_in': datetime(2026, 6, 10, 18, 0),
            'check_out': datetime(2026, 6, 10, 22, 0), 'work_entry_type_id': self.overtime_type.id})
        attendance.with_context(skip_time_rules=True).write({'state': 'validated'})
        return attendance

    def payslip(self, employee):
        with Form(self.env['hr.payslip'].with_company(employee.company_id)) as form:
            form.employee_id = employee
            form.date_from = date(2026, 6, 1)
            form.date_to = date(2026, 6, 28)
        payslip = form.record
        payslip.compute_sheet()
        return payslip

    def test_each_payslip_pays_its_own_overtime(self):
        overtime_a, overtime_b = self.overtime(self.employee_a), self.overtime(self.employee_b)
        payslip_b = self.payslip(self.employee_b)
        # 3,000 / 20 days of company B / 8 h = 18.75 an hour, x 4 h x 150%
        self.assertEqual(sum(payslip_b.line_ids.filtered(lambda line: line.code == 'OVERTIME').mapped('total')), 112.5)
        self.assertEqual(overtime_b.payslip_id, payslip_b)
        self.assertFalse(overtime_a.payslip_id)
