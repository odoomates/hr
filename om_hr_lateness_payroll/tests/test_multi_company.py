from datetime import date, datetime

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestLatenessPayrollMultiCompany(TransactionCase):
    """ Two companies sharing a lateness policy: the penalties of a company are computed for its employees only. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env['res.company'].create({'name': 'Lateness Company B'})
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Shared 8-17', 'company_id': False, 'attendance_ids': [
                Command.create({'dayofweek': str(day), 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'})
                for day in range(5)] + [
                Command.create({'dayofweek': str(day), 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
                for day in range(5)]})
        cls.policy = cls.env['hr.lateness.policy'].create({
            'name': 'Shared Late Policy', 'company_id': False, 'grace_in': 5, 'early_out': False, 'line_ids': [
                Command.create({'minutes_from': 0, 'occurrence': 1, 'penalty': 'fixed', 'amount': 20})]})
        cls.employee_a = cls.late_employee(cls.env.company, 'Late A')
        cls.employee_b = cls.late_employee(cls.company_b, 'Late B')
        cls.officer = new_test_user(
            cls.env, 'om_mc_late_officer', company_id=cls.env.company.id,
            company_ids=[Command.set(cls.env.company.ids)],
            groups='base.group_user,om_hr_payroll.group_hr_payroll_user,hr_attendance.group_hr_attendance_user')

    @classmethod
    def late_employee(cls, company, name):
        employee = cls.env['hr.employee'].with_company(company).create({
            'name': name, 'company_id': company.id, 'tz': 'UTC', 'resource_calendar_id': cls.calendar.id,
            'lateness_policy_id': cls.policy.id, 'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1), 'wage': 3000.0})
        employee.version_id.resource_calendar_id = cls.calendar
        cls.env['hr.attendance'].create({
            'employee_id': employee.id, 'check_in': datetime(2026, 9, 7, 8, 15),
            'check_out': datetime(2026, 9, 7, 17, 0)})
        return employee

    def test_penalties_of_the_companies_of_the_user(self):
        wizard = self.env['hr.lateness.penalty.wizard'].with_user(self.officer).create({'month': date(2026, 9, 1)})
        wizard.action_compute()
        adjustments = self.env['hr.payroll.adjustment'].search(
            [('type_id', '=', self.env.ref('om_hr_lateness_payroll.adjustment_type_lateness').id)])
        self.assertIn(self.employee_a, adjustments.employee_id)
        self.assertNotIn(self.employee_b, adjustments.employee_id, 'company B is not computed from company A')
        self.assertEqual(adjustments.company_id, self.env.company)

    def test_no_penalty_on_an_adjustment_of_another_company(self):
        adjustment_a = self.env['hr.lateness']._compute_penalties(date(2026, 9, 1), self.employee_a)
        lateness_b = self.env['hr.lateness'].search([('employee_id', '=', self.employee_b.id)])
        self.assertTrue(lateness_b)
        with self.assertRaises(UserError):
            lateness_b.adjustment_id = adjustment_a
