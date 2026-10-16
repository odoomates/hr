from datetime import date, datetime
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestLatenessPayroll(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.officer = new_test_user(cls.env, 'om_late_pay_officer',
                                    groups='base.group_user,om_hr_payroll.group_hr_payroll_user,'
                                           'hr_attendance.group_hr_attendance_user')
        cls.env.company.om_payroll_month_days = 30
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Late Pay 8-17', 'attendance_ids': [
                Command.create({'dayofweek': str(day), 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'})
                for day in range(5)] + [
                Command.create({'dayofweek': str(day), 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
                for day in range(5)]})
        cls.policy = cls.env['hr.lateness.policy'].create({
            'name': 'Pay Policy', 'grace_in': 5, 'early_out': False, 'line_ids': [
                Command.create({'minutes_from': 0, 'minutes_to': 30, 'occurrence': 1, 'penalty': 'fixed',
                                'amount': 20}),
                Command.create({'minutes_from': 0, 'minutes_to': 30, 'occurrence': 2, 'penalty': 'daily_percent',
                                'percent': 10}),
                Command.create({'minutes_from': 31, 'occurrence': 1, 'penalty': 'minutes', 'factor': 2}),
            ]})
        cls.late_type = cls.env.ref('om_hr_lateness_payroll.adjustment_type_lateness')
        basic = cls.env['hr.salary.rule'].create({
            'name': 'Basic', 'code': 'BASIC', 'sequence': 1, 'category_id': cls.env.ref('om_hr_payroll.BASIC').id,
            'amount_select': 'code', 'amount_python_compute': 'result = contract.wage'})
        net = cls.env.ref('om_hr_payroll.hr_rule_net')
        rules = basic | cls.late_type.rule_id
        if 'account_debit' in rules._fields:
            # payroll accounting is installed: a confirmed payslip is posted, so the rules need accounts
            cls.env['account.journal'].create({'name': 'Payroll Lateness', 'code': 'PAYLT', 'type': 'general'})
            rules.sudo().write({
                'account_debit': cls.env['account.account'].create({
                    'name': 'Payroll Expense Late', 'code': 'PAYEXPLT', 'account_type': 'expense'}).id,
                'account_credit': cls.env['account.account'].create({
                    'name': 'Payroll Payable Late', 'code': 'PAYPAYLT', 'account_type': 'liability_current'}).id,
            })
            net.sudo().write({'account_debit': False, 'account_credit': False})
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Lateness Structure', 'code': 'LATES', 'rule_ids': [Command.set((rules | net).ids)]})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Late Payee', 'tz': 'UTC', 'resource_calendar_id': cls.calendar.id,
            'lateness_policy_id': cls.policy.id, 'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1), 'wage': 3000.0, 'struct_id': cls.structure.id})
        cls.employee.version_id.resource_calendar_id = cls.calendar

    def attend(self, day, hour, minute):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id, 'check_in': datetime(2026, 9, day, hour, minute),
            'check_out': datetime(2026, 9, day, 17, 0)})

    def setUp(self):
        super().setUp()
        self.attend(7, 8, 15)   # 15 min, 1st: 20
        self.attend(8, 8, 15)   # 15 min, 2nd: 10% of 100
        self.attend(9, 9, 0)    # 60 min: 1 h x 12.5 x 2

    def compute(self):
        return self.env['hr.lateness'].with_user(self.officer)._compute_penalties(date(2026, 9, 1),
                                                                                        self.employee)

    def lateness(self):
        return self.env['hr.lateness'].search([('employee_id', '=', self.employee.id)], order='date')

    def payslip(self):
        with Form(self.env['hr.payslip']) as form:
            form.employee_id = self.employee
            form.date_from = date(2026, 9, 1)
            form.date_to = date(2026, 9, 30)
        payslip = form.record
        payslip.compute_sheet()
        return payslip

    def test_penalties_to_payslip(self):
        adjustment = self.compute()
        self.assertEqual((adjustment.type_id, adjustment.amount, adjustment.state),
                         (self.late_type, 55.0, 'running'))
        self.assertEqual(self.lateness().mapped('penalty_amount'), [20, 10, 25])
        self.assertEqual(adjustment.lateness_ids, self.lateness())
        self.assertIn('3 late arrivals', adjustment.description)
        self.assertEqual(self.compute(), adjustment, 'computed again: the same adjustment')
        payslip = self.payslip()
        self.assertEqual(sum(payslip.line_ids.filtered(lambda l: l.code == 'ADJ_LATE').mapped('total')), -55)

    def test_excuse_follows(self):
        adjustment = self.compute()
        self.lateness()[1].with_user(self.officer)._excuse('Doctor')
        self.assertEqual(adjustment.amount, 45, 'the excused 10 goes')
        self.assertEqual(self.lateness().mapped('penalty_amount'), [20, 0, 25])
        self.lateness()[0].with_user(self.officer)._excuse('Traffic')
        self.lateness()[2].with_user(self.officer)._excuse('Errand')
        self.assertEqual(adjustment.state, 'cancel', 'nothing left to take off')

    def test_paid_stays(self):
        adjustment = self.compute()
        self.payslip().action_payslip_done()
        self.assertEqual(adjustment.state, 'done')
        with self.assertRaises(UserError):
            self.lateness()[0].with_user(self.officer)._excuse('Too late')
        self.lateness()[0].sudo().write({'minutes': 25})
        self.compute()
        self.assertEqual(adjustment.amount, 55, 'a payslip took it: it stays')

    def test_monthly_cap(self):
        self.policy.monthly_cap_days = 0.3
        self.assertEqual(self.compute().amount, 30)

    def test_attendance_based_minutes_left_out(self):
        if 'attendance_based' not in self.employee.version_id._fields:
            return
        self.employee.version_id.attendance_based = True
        self.assertEqual(self.compute().amount, 30, 'the hour late is taken off by the Attendance Adjustment')

    def test_cron_on_the_first(self):
        Lateness = self.env['hr.lateness']
        with patch.object(fields.Date, 'context_today', lambda *args, **kwargs: date(2026, 10, 2)):
            Lateness._cron_lateness_penalties()
        self.assertFalse(self.lateness().adjustment_id, 'not the 1st')
        with patch.object(fields.Date, 'context_today', lambda *args, **kwargs: date(2026, 10, 1)):
            Lateness._cron_lateness_penalties()
            self.assertFalse(self.lateness().adjustment_id, 'not asked for')
            self.employee.company_id.lateness_auto_penalties = True
            Lateness._cron_lateness_penalties()
        self.assertEqual(self.lateness().adjustment_id.amount, 55)

    def test_wizard_for_payroll_only(self):
        wizard = self.env['hr.lateness.penalty.wizard'].with_user(self.officer).create(
            {'month': date(2026, 9, 1), 'employee_ids': [Command.set(self.employee.ids)]})
        action = wizard.action_compute()
        self.assertEqual(self.env['hr.payroll.adjustment'].search(action['domain']).amount, 55)
        user = new_test_user(self.env, 'om_late_nobody', groups='base.group_user')
        with self.assertRaises((UserError, AccessError)):
            self.env['hr.lateness.penalty.wizard'].with_user(user).create({'month': date(2026, 9, 1)})
