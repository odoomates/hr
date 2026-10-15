from datetime import date, datetime

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestWorkEntries(TransactionCase):
    """ Pay from the work entries of core Odoo. June 2026: 22 working days of 8 hours, 176 hours. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.write({'om_payroll_worked_days_source': 'work_entries', 'om_payroll_month_days': 30})
        cls.calendar = cls.env['resource.calendar'].create({'name': 'Work Entries 40h'})
        Rule = cls.env['hr.salary.rule']
        cls.rules = (cls.env.ref('om_hr_payroll.hr_rule_basic') | cls.env.ref('om_hr_payroll.hr_rule_hourly')
                     | cls.env.ref('om_hr_payroll.hr_rule_unpaid_leave')
                     | cls.env.ref('om_hr_payroll.hr_rule_attendance_adjustment')
                     | cls.env.ref('om_hr_payroll.hr_rule_net'))
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Work Entries Structure', 'code': 'WETEST', 'parent_id': False,
            'rule_ids': [Command.set(cls.rules.ids)]})
        cls.unpaid = cls._time_type('WE Unpaid', 0.0)
        cls.half = cls._time_type('WE Half Paid', 0.5)
        if 'hr.time.rule' in cls.env:
            cls.env['hr.time.rule'].search([]).write({'active': False})

    @classmethod
    def _time_type(cls, name, rate):
        return cls.env['hr.work.entry.type'].create({
            'name': name, 'code': name.upper().replace(' ', '_'), 'count_as': 'absence', 'amount_rate': rate,
            'requires_allocation': False, 'time_off_selectable': True})

    def needs_attendances(self):
        """ The contracts based on attendances come with the Attendances app, which payroll does not need. """
        if 'attendance_based' not in self.env['hr.version']._fields:
            self.skipTest('needs the Attendances app')

    def employee(self, **values):
        return self.env['hr.employee'].create({
            'name': 'Work Entries Employee', 'tz': 'UTC', 'resource_calendar_id': self.calendar.id,
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1), 'wage': 4400.0,
            'struct_id': self.structure.id, **values})

    def leave(self, employee, time_type, date_from, date_to):
        leave = self.env['hr.leave'].create({
            'name': time_type.name, 'employee_id': employee.id, 'work_entry_type_id': time_type.id,
            'request_date_from': date_from, 'request_date_to': date_to})
        if leave.state != 'validate':
            leave.sudo().action_approve()
        return leave

    def attend(self, employee, days):
        """ Full days of 8 hours, the first working days of June 2026. """
        workdays = [day for day in range(1, 31) if date(2026, 6, day).weekday() < 5][:days]
        self.env['hr.attendance'].create([
            {'employee_id': employee.id, 'check_in': datetime(2026, 6, day, start, 0),
             'check_out': datetime(2026, 6, day, start + 4, 0)}
            for day in workdays for start in (8, 13)])

    def payslip(self, employee):
        with Form(self.env['hr.payslip']) as form:
            form.employee_id = employee
            form.date_from = date(2026, 6, 1)
            form.date_to = date(2026, 6, 30)
        payslip = form.record
        payslip.compute_sheet()
        return payslip

    @staticmethod
    def totals(payslip):
        return {line.code: round(line.total, 2) for line in payslip.line_ids}

    @staticmethod
    def worked_days(payslip):
        return {line.code: (round(line.number_of_days, 2), round(line.number_of_hours, 2))
                for line in payslip.worked_days_line_ids}

    def test_schedule_based_same_as_before(self):
        """ The work entries give the payslips of the working schedule: upgrading changes nothing. """
        employee = self.employee()
        self.leave(employee, self.unpaid, date(2026, 6, 8), date(2026, 6, 9))
        from_entries = self.payslip(employee)
        self.env.company.om_payroll_worked_days_source = 'schedule'
        from_schedule = self.payslip(employee)
        self.assertEqual(self.worked_days(from_entries), self.worked_days(from_schedule))
        self.assertEqual(self.worked_days(from_entries)['WORK100'], (22.0, 176.0))
        self.assertEqual(self.totals(from_entries), self.totals(from_schedule))
        self.assertEqual(self.totals(from_entries)['NET'], 4000.0, '2 unpaid days out of 22')

    def test_monthly_paid_on_attendances(self):
        self.needs_attendances()
        employee = self.employee(attendance_based=True)
        self.attend(employee, 20)
        payslip = self.payslip(employee)
        lines = self.worked_days(payslip)
        self.assertEqual(lines['WORK100'], (22.0, 176.0))
        self.assertEqual(lines['ATTENDED'], (20.0, 160.0))
        totals = self.totals(payslip)
        self.assertEqual(totals['ATTADJ'], -400.0, '16 hours of 176 neither worked nor on time off')
        self.assertEqual(totals['NET'], 4000.0)

    def test_attendances_and_time_off(self):
        """ A day of time off is not missing: the time off rules pay or take it off. """
        self.needs_attendances()
        employee = self.employee(attendance_based=True)
        self.attend(employee, 21)
        self.leave(employee, self.unpaid, date(2026, 6, 30), date(2026, 6, 30))
        totals = self.totals(self.payslip(employee))
        self.assertNotIn('ATTADJ', totals)
        self.assertEqual(totals['UNPAID'], -200.0)
        self.assertEqual(totals['NET'], 4200.0)

    def test_hourly_on_the_working_schedule(self):
        employee = self.employee(wage=0.0, wage_type='hourly', hourly_wage=25.0)
        self.leave(employee, self.half, date(2026, 6, 8), date(2026, 6, 8))
        totals = self.totals(self.payslip(employee))
        self.assertEqual(totals['HOURLY'], 4300.0, '168 hours worked and 8 hours of time off at half: 172 hours')
        self.assertEqual(totals['NET'], 4300.0)

    def test_hourly_on_attendances_and_overtime_left_out(self):
        self.needs_attendances()
        employee = self.employee(wage=0.0, wage_type='hourly', hourly_wage=25.0, attendance_based=True)
        self.attend(employee, 10)
        overtime_type = self.env['hr.work.entry.type'].create({'name': 'WE Overtime', 'code': 'WEOT'})
        rule = self.env['hr.time.rule'].create({'name': 'WE Overtime Rule', 'work_entry_type_id': overtime_type.id,
                                                'active': False})
        self.env['hr.attendance'].with_context(skip_time_rules=True).create({
            'employee_id': employee.id, 'check_in': datetime(2026, 6, 20, 9, 0),
            'check_out': datetime(2026, 6, 20, 13, 0), 'work_entry_type_id': overtime_type.id,
            'time_rule_id': rule.id, 'state': 'validated'})
        payslip = self.payslip(employee)
        self.assertEqual(self.worked_days(payslip)['ATTENDED'], (10.0, 80.0), 'the overtime is not base pay')
        self.assertEqual(self.totals(payslip)['HOURLY'], 2000.0)

    def test_hourly_contract_has_no_fixed_wage(self):
        with self.assertRaises(ValidationError):
            self.employee(wage_type='hourly', hourly_wage=25.0)

    def test_daily_and_hourly_wage_in_rules(self):
        rule = self.env['hr.salary.rule'].create({
            'name': 'Day', 'code': 'DAY', 'sequence': 50, 'category_id': self.env.ref('om_hr_payroll.ALW').id,
            'amount_select': 'code', 'amount_python_compute': 'result = daily_wage + hourly_wage'})
        self.structure.rule_ids |= rule
        self.env.company.om_payroll_month_days = 22
        self.assertEqual(self.totals(self.payslip(self.employee()))['DAY'], 225.0, '4400 / 22 = 200, / 8 = 25')

    def test_hours_not_due_yet_are_not_missing(self):
        """ A payslip computed in the middle of its period: only the days up to today are due. """
        self.needs_attendances()
        employee = self.employee(attendance_based=True)
        self.attend(employee, 10)
        with freeze_time('2026-06-12'):
            payslip = self.payslip(employee)
            lines = self.worked_days(payslip)
        self.assertEqual(lines['WORK100'], (10.0, 80.0), 'June 1 to 12: 10 working days')
        self.assertNotIn('ATTADJ', self.totals(payslip))
