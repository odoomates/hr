from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestExitPayrollMultiCompany(TransactionCase):
    """ The final settlement of an exit is a payslip of the company of the exit. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env['res.company'].create({'name': 'Exits Company B'})
        if 'journal_id' in cls.env['hr.payslip']._fields:
            cls.env['account.journal'].create({
                'name': 'Salaries B', 'code': 'SALEB', 'type': 'general', 'company_id': cls.company_b.id})
        rules = cls.env.ref('om_hr_payroll.hr_rule_basic') | cls.env.ref('om_hr_payroll.hr_rule_net')
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Shared Exits', 'code': 'EXITMC', 'parent_id': False, 'company_id': False,
            'rule_ids': [Command.set(rules.ids)]})
        cls.exit_a = cls.approved_exit(cls.env.company, 'Leaver A')
        cls.exit_b = cls.approved_exit(cls.company_b, 'Leaver B')

    @classmethod
    def approved_exit(cls, company, name):
        employee = cls.env['hr.employee'].with_company(company).create({
            'name': name, 'company_id': company.id, 'tz': 'UTC', 'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1), 'wage': 3000.0, 'struct_id': cls.structure.id})
        exit_ = cls.env['hr.exit'].with_company(company).create({
            'employee_id': employee.id, 'date_notice': date(2026, 7, 21), 'notice_days': 30})
        exit_.write({'state': 'approved', 'approval_state': 'approved'})
        return exit_

    def test_settlement_in_the_company_of_the_exit(self):
        self.assertEqual(self.exit_b.company_id, self.company_b)
        self.exit_b.with_company(self.env.company).action_final_settlement()
        payslip = self.exit_b.settlement_payslip_id
        self.assertEqual((payslip.company_id, payslip.employee_id), (self.company_b, self.exit_b.employee_id))

    def test_no_settlement_of_another_company(self):
        self.exit_a.action_final_settlement()
        with self.assertRaises(UserError):
            self.exit_a.settlement_payslip_id.exit_id = self.exit_b
