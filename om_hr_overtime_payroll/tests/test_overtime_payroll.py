from datetime import date, datetime

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestOvertimePayroll(TransactionCase):
    """ 3,000 a month, 30 days, 8 hours a day: the hourly wage is 12.50. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.om_payroll_month_days = 30
        cls.calendar = cls.env['resource.calendar'].create({'name': 'Overtime 40h'})
        rules = cls.env.ref('om_hr_payroll.hr_rule_basic') | cls.env.ref('om_hr_overtime_payroll.hr_rule_overtime') \
            | cls.env.ref('om_hr_payroll.hr_rule_net')
        structure = cls.env['hr.payroll.structure'].create({
            'name': 'Overtime Structure', 'code': 'OTTEST', 'parent_id': False, 'rule_ids': [Command.set(rules.ids)]})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Overtime Worker', 'tz': 'UTC', 'resource_calendar_id': cls.calendar.id,
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1), 'wage': 3000.0,
            'struct_id': structure.id})
        cls.overtime_type = cls.env['hr.work.entry.type'].create({
            'name': 'Test Overtime', 'code': 'TESTOT', 'amount_rate': 2.0})
        cls.rule = cls.env['hr.time.rule'].create({
            'name': 'Test Weekday Overtime', 'work_entry_type_id': cls.overtime_type.id})
        cls.rule.amount_rate = 1.5

    def overtime(self, day, hours=4, state='validated', rule=True):
        attendance = self.env['hr.attendance'].with_context(skip_time_rules=True).create({
            'employee_id': self.employee.id,
            'check_in': datetime(day.year, day.month, day.day, 18, 0),
            'check_out': datetime(day.year, day.month, day.day, 18 + hours, 0),
            'work_entry_type_id': self.overtime_type.id,
            'time_rule_id': self.rule.id if rule else False,
        })
        attendance.with_context(skip_time_rules=True).write({'state': state})
        return attendance

    def payslip(self, month):
        with Form(self.env['hr.payslip']) as form:
            form.employee_id = self.employee
            form.date_from = date(2026, month, 1)
            form.date_to = date(2026, month, 28)
        payslip = form.record
        payslip.compute_sheet()
        return payslip

    @staticmethod
    def total(payslip, code):
        return sum(payslip.line_ids.filtered(lambda line: line.code == code).mapped('total'))

    def test_validated_overtime_is_paid_at_the_rule_rate(self):
        paid = self.overtime(date(2026, 6, 10))
        draft = self.overtime(date(2026, 6, 11), state='draft')
        refused = self.overtime(date(2026, 6, 12), state='refused')
        june = self.payslip(6)
        self.assertEqual(self.total(june, 'OVERTIME'), 75.0, '4 h x 12.50 x 150%')
        self.assertEqual(self.total(june, 'NET'), 3075.0)
        self.assertEqual(june.om_overtime_ids, paid)
        self.assertFalse((draft | refused).om_payslip_id)
        self.assertEqual(june.om_overtime_hours, 4.0)

    def test_overtime_entered_by_hand_uses_the_type_rate(self):
        self.overtime(date(2026, 6, 10), rule=False)
        self.assertEqual(self.total(self.payslip(6), 'OVERTIME'), 100.0, '4 h x 12.50 x 200%')

    def test_paid_once_and_late_validation(self):
        june_overtime = self.overtime(date(2026, 6, 10))
        june = self.payslip(6)
        june.write({'state': 'done'})
        late = self.overtime(date(2026, 6, 20), hours=2, state='draft')
        late.with_context(skip_time_rules=True).write({'state': 'validated'})
        july = self.payslip(7)
        self.assertEqual(july.om_overtime_ids, late, 'June overtime validated after the June payslip')
        self.assertEqual(self.total(july, 'OVERTIME'), 37.5)
        self.assertEqual(june_overtime.om_payslip_id, june)

    def test_cancelled_payslip_releases_the_overtime(self):
        overtime = self.overtime(date(2026, 6, 10))
        june = self.payslip(6)
        june.action_payslip_cancel()
        self.assertFalse(overtime.om_payslip_id)
        self.assertEqual(self.payslip(6).om_overtime_ids, overtime)

    def test_recompute_does_not_double(self):
        self.overtime(date(2026, 6, 10))
        june = self.payslip(6)
        june.compute_sheet()
        self.assertEqual(self.total(june, 'OVERTIME'), 75.0)
        self.assertEqual(len(june.input_line_ids.filtered(lambda line: line.code == 'OVERTIME')), 1)

    def test_base_structure_pays_overtime(self):
        self.assertIn(self.env.ref('om_hr_overtime_payroll.hr_rule_overtime'),
                      self.env.ref('om_hr_payroll.structure_base').rule_ids)

    def test_overtime_from_the_time_rules_of_attendances(self):
        """ A 12 hour day against an 8 hour schedule, through the rules of the Attendances app. """
        self.env['hr.time.rule'].search([]).write({'active': False})
        rule = self.env['hr.time.rule'].create({
            'name': 'Daily Overtime (Test)', 'calendar_source': 'employee', 'quantity_period': 'day',
            'work_entry_type_id': self.overtime_type.id,
            'condition_work_entry_type_ids': [(4, self.env.company._get_default_attendance_work_entry_type().id)],
        })
        rule.amount_rate = 1.5
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 6, 9, 7, 0),
            'check_out': datetime(2026, 6, 9, 19, 0),
            'state': 'validated',
        })
        outputs = self.env['hr.attendance'].search([('employee_id', '=', self.employee.id),
                                                    ('time_rule_id', '=', rule.id)])
        self.assertAlmostEqual(sum(outputs.mapped('worked_hours')), 4.0)
        june = self.payslip(6)
        self.assertEqual(june.om_overtime_ids, outputs)
        self.assertEqual(self.total(june, 'OVERTIME'), 75.0)
