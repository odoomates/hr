from datetime import date

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestFinalSettlement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Rule = cls.env['hr.salary.rule']
        basic = Rule.create({
            'name': 'Basic', 'code': 'BASIC', 'sequence': 1, 'category_id': cls.env.ref('om_hr_payroll.BASIC').id,
            'amount_select': 'code', 'amount_python_compute': 'result = contract.wage'})
        rules = basic | cls.env.ref('om_hr_payroll.hr_rule_partial_period') \
            | cls.env.ref('om_hr_exit_payroll.hr_rule_leave_encashment') \
            | cls.env.ref('om_hr_exit_payroll.hr_rule_gratuity') | cls.env.ref('om_hr_payroll.hr_rule_net')
        cls.loan_rule = cls.env.ref('om_hr_loan_payroll.hr_rule_loan', raise_if_not_found=False)
        if cls.loan_rule:
            rules |= cls.loan_rule
        if 'account_debit' in Rule._fields:
            # payroll accounting is installed: a confirmed payslip is posted, so the rules need accounts
            cls.env['account.journal'].create({'name': 'Payroll Exit', 'code': 'PAYEX', 'type': 'general'})
            (rules - cls.env.ref('om_hr_payroll.hr_rule_net')).write({
                'account_debit': cls.env['account.account'].create({
                    'name': 'Payroll Expense Exit', 'code': 'PAYEXPEX', 'account_type': 'expense'}).id,
                'account_credit': cls.env['account.account'].create({
                    'name': 'Payroll Payable Exit', 'code': 'PAYPAYEX', 'account_type': 'liability_current'}).id,
            })
            cls.env.ref('om_hr_payroll.hr_rule_net').write({'account_debit': False, 'account_credit': False})
        structure = cls.env['hr.payroll.structure'].create({
            'name': 'Exit Structure', 'code': 'EXITS', 'rule_ids': [Command.set(rules.ids)]})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Leaver', 'tz': 'UTC', 'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1), 'wage': 3000.0, 'struct_id': structure.id})
        annual = cls.env['hr.work.entry.type'].create({
            'name': 'Annual Leave', 'code': 'OMANNUAL', 'count_as': 'absence', 'requires_allocation': True,
            'request_unit': 'day', 'unit_of_measure': 'day', 'encashable': True})
        allocation = cls.env['hr.leave.allocation'].create({
            'name': 'Annual 2026', 'employee_id': cls.employee.id, 'work_entry_type_id': annual.id,
            'number_of_days': 10, 'date_from': date(2026, 1, 1)})
        allocation.action_approve()
        cls.exit = cls.env['hr.exit'].create({
            'employee_id': cls.employee.id, 'date_notice': date(2026, 7, 21), 'notice_days': 30})
        cls.exit.write({'state': 'approved', 'approval_state': 'approved'})

    @staticmethod
    def total(payslip, code):
        return sum(payslip.line_ids.filtered(lambda line: line.code == code).mapped('total'))

    def test_settlement(self):
        self.assertEqual(self.exit.last_working_day, date(2026, 8, 20))
        self.assertEqual(self.exit.encashment_days, 10)
        self.assertEqual(self.exit.encashment_amount, 1000)
        if 'gratuity_amount' in self.exit._fields:
            self.exit.gratuity_amount = 750
        loan = None
        if self.loan_rule:
            loan_type = self.env['hr.loan.type'].create({'name': 'Exit Loan'})
            loan = self.env['hr.loan'].create({
                'employee_id': self.employee.id, 'type_id': loan_type.id, 'amount': 600, 'installment_count': 3,
                'date': date(2026, 6, 1), 'date_start': date(2026, 8, 1)})
            loan._compute_installments()
            loan.write({'state': 'running', 'approval_state': 'approved'})

        self.exit.action_final_settlement()
        payslip = self.exit.settlement_payslip_id
        self.assertEqual((payslip.date_from, payslip.date_to), (date(2026, 8, 1), date(2026, 8, 20)))
        self.assertEqual(payslip.exit_id, self.exit)
        self.assertEqual(self.total(payslip, 'LEAVE_ENCASH'), 1000)
        # up to Thursday 20 August: 14 working days out of the 21 of the month
        self.assertAlmostEqual(self.total(payslip, 'PARTIAL'), -1000)
        expected_net = 2000 + 1000
        if 'gratuity_amount' in self.exit._fields:
            self.assertEqual(self.total(payslip, 'GRATUITY'), 750)
            expected_net += 750
        if loan:
            self.assertEqual(self.total(payslip, 'LOAN'), -600, 'every installment still due is deducted')
            expected_net -= 600
        self.assertEqual(self.total(payslip, 'NET'), expected_net)

        payslip.action_payslip_done()
        if loan:
            self.assertEqual(loan.state, 'paid')
        self.assertEqual(self.exit.action_final_settlement()['res_id'], payslip.id, 'one settlement per exit')

    def test_encashment_follows_the_payroll_days_per_month(self):
        self.env.company.om_payroll_month_days = 20
        self.exit.invalidate_recordset()
        self.assertEqual(self.exit.encashment_amount, 1500, '10 days of 3000 / 20')
