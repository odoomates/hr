from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestShiftPayrollMultiCompany(TransactionCase):
    """ Two companies sharing the shift allowance rule and a night shift: each payslip pays its own company's. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env['res.company'].create({'name': 'Shifts Company B'})
        if 'journal_id' in cls.env['hr.payslip']._fields:
            cls.env['account.journal'].create({
                'name': 'Salaries B', 'code': 'SALSB', 'type': 'general', 'company_id': cls.company_b.id})
        night = cls.env.ref('om_hr_shift.template_night')
        cls.night = night.copy({'name': 'Shared Night', 'company_id': False, 'allowance': 20.0})
        rules = cls.env.ref('om_hr_payroll.hr_rule_basic') \
            | cls.env.ref('om_hr_shift_payroll.hr_rule_shift_allowance') | cls.env.ref('om_hr_payroll.hr_rule_net')
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Shared Shifts', 'code': 'SHIFTMC', 'parent_id': False, 'company_id': False,
            'rule_ids': [Command.set(rules.ids)]})
        cls.employee_a = cls.night_worker(cls.env.company, 'Night A')
        cls.employee_b = cls.night_worker(cls.company_b, 'Night B')

    @classmethod
    def night_worker(cls, company, name):
        employee = cls.env['hr.employee'].with_company(company).create({
            'name': name, 'company_id': company.id, 'tz': 'UTC', 'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1), 'wage': 3000.0, 'struct_id': cls.structure.id})
        employee.with_company(company)._start_rostering(date(2026, 9, 1))
        shifts = cls.env['hr.shift'].with_company(company).create([
            dict(cls.night._shift_values(), employee_id=employee.id, date=date(2026, 9, day)) for day in (7, 8, 9)])
        shifts.with_context(om_shift_override=True).action_publish()
        return employee

    def payslip(self, employee):
        with Form(self.env['hr.payslip'].with_company(employee.company_id)) as form:
            form.employee_id = employee
            form.date_from = date(2026, 9, 1)
            form.date_to = date(2026, 9, 28)
        payslip = form.record
        payslip.compute_sheet()
        return payslip

    def test_each_payslip_pays_the_shifts_of_its_company(self):
        payslip_b = self.payslip(self.employee_b)
        self.assertEqual(sum(payslip_b.line_ids.filtered(lambda line: line.code == 'SHIFT_ALW').mapped('total')), 60.0)
        self.assertEqual(payslip_b.shift_ids.company_id, self.company_b)
        self.assertEqual(payslip_b.shift_ids.employee_id, self.employee_b)

    def test_no_shift_on_a_payslip_of_another_company(self):
        payslip_b = self.payslip(self.employee_b)
        shift_a = self.env['hr.shift'].search([('employee_id', '=', self.employee_a.id)], limit=1)
        with self.assertRaises(UserError):
            shift_a.sudo().payslip_id = payslip_b
