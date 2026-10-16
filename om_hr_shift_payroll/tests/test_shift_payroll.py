from datetime import date, datetime

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestShiftPayroll(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.night = cls.env.ref('om_hr_shift.template_night')
        cls.night.allowance = 20.0
        cls.rule = cls.env.ref('om_hr_shift_payroll.hr_rule_shift_allowance')
        basic = cls.env['hr.salary.rule'].create({
            'name': 'Basic', 'code': 'BASIC', 'sequence': 1, 'category_id': cls.env.ref('om_hr_payroll.BASIC').id,
            'amount_select': 'code', 'amount_python_compute': 'result = contract.wage'})
        net = cls.env.ref('om_hr_payroll.hr_rule_net')
        rules = basic | cls.rule
        if 'account_debit' in rules._fields:
            # payroll accounting is installed: a confirmed payslip is posted, so the rules need accounts
            cls.env['account.journal'].create({'name': 'Payroll Shifts', 'code': 'PAYSH', 'type': 'general'})
            rules.sudo().write({
                'account_debit': cls.env['account.account'].create({
                    'name': 'Payroll Expense Shift', 'code': 'PAYEXPSH', 'account_type': 'expense'}).id,
                'account_credit': cls.env['account.account'].create({
                    'name': 'Payroll Payable Shift', 'code': 'PAYPAYSH', 'account_type': 'liability_current'}).id,
            })
            net.sudo().write({'account_debit': False, 'account_credit': False})
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Shift Structure', 'code': 'SHIFTS', 'rule_ids': [Command.set((rules | net).ids)]})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Night Worker', 'tz': 'UTC', 'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1), 'wage': 3000.0, 'struct_id': cls.structure.id})
        cls.employee._start_rostering(date(2026, 9, 1))
        cls.shifts = cls.env['hr.shift'].create([
            dict(cls.night._shift_values(), employee_id=cls.employee.id, date=date(2026, 9, day)) for day in (7, 8, 9)])
        cls.shifts.with_context(om_shift_override=True).action_publish()

    def payslip(self, month):
        with Form(self.env['hr.payslip']) as form:
            form.employee_id = self.employee
            form.date_from = date(2026, month, 1)
            form.date_to = date(2026, month, 28)
        payslip = form.record
        payslip.compute_sheet()
        return payslip

    @staticmethod
    def total(payslip):
        return sum(payslip.line_ids.filtered(lambda line: line.code == 'SHIFT_ALW').mapped('total'))

    def test_base_structure_pays_allowances(self):
        self.assertIn(self.rule, self.env.ref('om_hr_payroll.structure_base').rule_ids)

    def test_paid_once_time_off_left_out(self):
        self.env['resource.calendar.leaves'].create({
            'name': 'Sick', 'resource_id': self.employee.resource_id.id,
            'date_from': datetime(2026, 9, 8, 0, 0), 'date_to': datetime(2026, 9, 10, 0, 0)})
        september = self.payslip(9)
        self.assertEqual(self.total(september), 40, 'the night on time off is not paid')
        self.assertEqual(september.shift_ids, self.shifts[0] | self.shifts[2])
        september.action_payslip_done()
        self.assertEqual(self.total(self.payslip(10)), 0, 'paid once')

    def test_released_by_cancel(self):
        september = self.payslip(9)
        self.assertEqual(self.total(september), 60)
        september.action_payslip_done()
        september.action_payslip_cancel()
        self.assertFalse(self.shifts.payslip_id)
        self.assertEqual(self.total(self.payslip(10)), 60, 'due again on the next payslip')
