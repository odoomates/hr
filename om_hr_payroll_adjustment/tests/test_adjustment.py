from datetime import date
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, TransactionCase, new_test_user, tagged

from odoo.addons.om_hr_payroll_adjustment.models.hr_payslip import HrPayslip


@tagged('post_install', '-at_install')
class TestAdjustment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.officer = new_test_user(cls.env, 'om_adj_officer', groups='base.group_user,om_hr_payroll.group_hr_payroll_user')
        cls.manager = new_test_user(cls.env, 'om_adj_manager',
                                    groups='base.group_user,om_hr_payroll.group_hr_payroll_manager')
        cls.employee_user = new_test_user(cls.env, 'om_adj_employee', groups='base.group_user')
        basic = cls.env['hr.salary.rule'].create({
            'name': 'Basic', 'code': 'BASIC', 'sequence': 1, 'category_id': cls.env.ref('om_hr_payroll.BASIC').id,
            'amount_select': 'code', 'amount_python_compute': 'result = contract.wage'})
        gross = cls.env.ref('om_hr_payroll.hr_rule_taxable')
        net = cls.env.ref('om_hr_payroll.hr_rule_net')
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Adjustment Structure', 'code': 'ADJS', 'rule_ids': [Command.set((basic | gross | net).ids)]})
        Type = cls.env['hr.payroll.adjustment.type']
        cls.bonus = Type.create({'name': 'Test Bonus', 'code': 'T_BONUS', 'kind': 'addition',
                                 'category_id': cls.env.ref('om_hr_payroll.ALW').id, 'require_approval': False,
                                 'structure_ids': [Command.set(cls.structure.ids)]})
        cls.fine = Type.create({'name': 'Test Fine', 'code': 'T_FINE', 'kind': 'deduction',
                                'category_id': cls.env.ref('om_hr_payroll.DED').id, 'require_approval': False,
                                'settle_at_exit': True, 'structure_ids': [Command.set(cls.structure.ids)]})
        cls.approved = Type.create({'name': 'Test Approved', 'code': 'T_APPROVED', 'kind': 'addition',
                                    'category_id': cls.env.ref('om_hr_payroll.ALW').id, 'require_approval': True,
                                    'structure_ids': [Command.set(cls.structure.ids)]})
        rules = basic | cls.bonus.rule_id | cls.fine.rule_id | cls.approved.rule_id
        if 'account_debit' in rules._fields:
            # payroll accounting is installed: a confirmed payslip is posted, so the rules need accounts
            cls.env['account.journal'].create({'name': 'Payroll Adjustments', 'code': 'PAYADJ', 'type': 'general'})
            rules.sudo().write({
                'account_debit': cls.env['account.account'].create({
                    'name': 'Payroll Expense Adj', 'code': 'PAYEXPADJ', 'account_type': 'expense'}).id,
                'account_credit': cls.env['account.account'].create({
                    'name': 'Payroll Payable Adj', 'code': 'PAYPAYADJ', 'account_type': 'liability_current'}).id,
            })
            (gross | net).sudo().write({'account_debit': False, 'account_credit': False})
        cls.department = cls.env['hr.department'].create({'name': 'Adjusted Department'})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Adjusted', 'tz': 'UTC', 'date_version': date(2026, 1, 1), 'user_id': cls.employee_user.id,
            'department_id': cls.department.id,
            'contract_date_start': date(2026, 1, 1), 'wage': 3000.0, 'struct_id': cls.structure.id})

    def adjustment(self, adjustment_type, confirm=True, **values):
        adjustment = self.env['hr.payroll.adjustment'].with_user(self.officer).create({
            'employee_id': self.employee.id, 'type_id': adjustment_type.id, 'date_start': date(2026, 8, 1),
            **values})
        if confirm:
            adjustment.action_confirm()
        return adjustment

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

    def test_type_keeps_its_rule(self):
        rule = self.bonus.rule_id
        self.assertEqual((rule.code, rule.category_id), ('T_BONUS', self.env.ref('om_hr_payroll.ALW')))
        self.assertIn(rule, self.structure.rule_ids)
        self.assertEqual(rule.input_ids.code, 'T_BONUS')
        self.bonus.write({'name': 'Renamed Bonus', 'code': 'T_BONUS2', 'structure_ids': [Command.clear()]})
        self.assertEqual((rule.name, rule.code, rule.input_ids.code), ('Renamed Bonus', 'T_BONUS2', 'T_BONUS2'))
        self.assertNotIn(rule, self.structure.rule_ids)
        self.assertIn('-inputs.T_FINE.amount', self.fine.rule_id.amount_python_compute, 'a deduction comes off')

    def test_once(self):
        adjustment = self.adjustment(self.bonus, amount=500.0)
        self.assertEqual(adjustment.state, 'running')
        self.assertEqual(self.total(self.payslip(7), 'T_BONUS'), 0, 'not before its month')
        august = self.payslip(8)
        self.assertEqual(self.total(august, 'T_BONUS'), 500)
        self.assertEqual(self.total(august, 'GROSS'), 3500)
        self.assertEqual(self.total(august, 'NET'), 3500)
        self.assertEqual(august.adjustment_line_ids, adjustment.line_ids)
        august.action_payslip_done()
        self.assertEqual(adjustment.state, 'done')
        self.assertEqual(adjustment.amount_done, 500)
        self.assertEqual(self.total(self.payslip(9), 'T_BONUS'), 0, 'paid once')

    def test_months(self):
        adjustment = self.adjustment(self.fine, recurrence='months', month_count=3, amount=200.0)
        self.assertEqual(len(adjustment.line_ids), 3)
        for month in (8, 9, 10):
            payslip = self.payslip(month)
            self.assertEqual(self.total(payslip, 'T_FINE'), -200)
            self.assertEqual(self.total(payslip, 'NET'), 2800)
            payslip.action_payslip_done()
        self.assertEqual(adjustment.state, 'done')

    def test_until_total(self):
        adjustment = self.adjustment(self.fine, recurrence='total', amount=500.0, total_amount=1200.0)
        self.assertEqual(adjustment.line_ids.mapped('amount'), [500, 500, 200], 'the last month takes the rest')
        self.assertEqual(adjustment.amount_residual, 1200)

    def test_percent_of_wage_until_total(self):
        adjustment = self.adjustment(self.fine, recurrence='total', amount_type='percent', percent=25,
                                     total_amount=1000.0)
        self.assertFalse(adjustment.line_ids, 'its months come with the payslips')
        august = self.payslip(8)
        self.assertEqual(self.total(august, 'T_FINE'), -750)
        august.action_payslip_done()
        september = self.payslip(9)
        self.assertEqual(self.total(september, 'T_FINE'), -250, 'never beyond the total')
        september.action_payslip_done()
        self.assertEqual(adjustment.state, 'done')
        self.assertEqual(adjustment.amount_done, 1000)
        self.assertEqual(self.total(self.payslip(10), 'T_FINE'), 0)

    def test_percent_of_gross(self):
        self.adjustment(self.bonus, amount=1000.0)
        self.adjustment(self.fine, amount_type='percent', percent=10, percent_base='gross')
        august = self.payslip(8)
        self.assertEqual(self.total(august, 'GROSS'), 4000)
        self.assertEqual(self.total(august, 'T_FINE'), -400, 'computed again with the gross')
        self.assertEqual(self.total(august, 'NET'), 3600)
        with self.assertRaises(UserError):
            self.adjustment(self.bonus, amount_type='percent', percent=10, percent_base='gross')

    def test_postpone_and_stop(self):
        adjustment = self.adjustment(self.fine, recurrence='months', month_count=3, amount=100.0)
        adjustment.line_ids[0].with_user(self.officer).action_postpone()
        self.assertEqual(adjustment.line_ids.mapped('date'),
                         [date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)])
        self.assertEqual(self.total(self.payslip(8), 'T_FINE'), 0)
        september = self.payslip(9)
        self.assertEqual(self.total(september, 'T_FINE'), -100)
        september.action_payslip_done()
        adjustment.with_user(self.officer).action_stop()
        self.assertEqual(adjustment.state, 'done')
        self.assertEqual(len(adjustment.line_ids), 1)
        self.assertEqual(self.total(self.payslip(10), 'T_FINE'), 0)

    def test_released_by_cancel(self):
        adjustment = self.adjustment(self.bonus, amount=500.0)
        august = self.payslip(8)
        august.action_payslip_done()
        self.assertEqual(adjustment.state, 'done')
        august.action_payslip_cancel()
        self.assertEqual(adjustment.state, 'running')
        self.assertEqual(adjustment.line_ids.state, 'to_pay')
        self.assertEqual(self.total(self.payslip(9), 'T_BONUS'), 500, 'due again, a month late')

    def test_exit_settles(self):
        fine = self.adjustment(self.fine, recurrence='months', month_count=3, amount=100.0)
        bonus = self.adjustment(self.bonus, recurrence='months', month_count=3, amount=50.0)
        with patch.object(HrPayslip, '_adjustment_settles_all', lambda payslip: True):
            august = self.payslip(8)
        self.assertEqual(self.total(august, 'T_FINE'), -300, 'everything due at exit')
        self.assertEqual(self.total(august, 'T_BONUS'), 50, 'a type not settled at exit keeps its months')
        self.assertEqual(len(fine.line_ids.filtered('payslip_id')), 3)
        self.assertEqual(len(bonus.line_ids.filtered('payslip_id')), 1)

    def test_approval(self):
        adjustment = self.adjustment(self.approved, amount=300.0)
        self.assertEqual(adjustment.state, 'to_approve')
        self.assertEqual(self.total(self.payslip(8), 'T_APPROVED'), 0, 'not before approved')
        self.assertIn(self.manager, adjustment.approver_user_ids)
        adjustment.with_user(self.manager).action_approval_approve()
        self.assertEqual(adjustment.state, 'running')
        self.assertEqual(self.total(self.payslip(9), 'T_APPROVED'), 300)

    def test_only_payroll_confirms(self):
        adjustment = self.adjustment(self.bonus, confirm=False, amount=100.0)
        with self.assertRaises((UserError, AccessError)):
            adjustment.with_user(self.employee_user).action_confirm()

    def test_wizard_for_a_department(self):
        other = self.env['hr.employee'].create({'name': 'Adjusted Too', 'department_id': self.department.id})
        wizard = self.env['hr.payroll.adjustment.wizard'].with_user(self.officer).create({
            'type_id': self.bonus.id, 'amount': 250.0, 'date_start': date(2026, 8, 1)})
        with Form(wizard) as form:
            form.department_id = self.department
        action = wizard.action_create()
        adjustments = self.env['hr.payroll.adjustment'].search(action['domain'])
        self.assertEqual(adjustments.employee_id, self.employee | other)
        self.assertEqual(set(adjustments.mapped('state')), {'running'})
        self.assertEqual(self.total(self.payslip(8), 'T_BONUS'), 250)

    def test_employee_sees_own(self):
        draft = self.adjustment(self.bonus, confirm=False, amount=100.0)
        running = self.adjustment(self.fine, amount=50.0)
        other = self.env['hr.employee'].create({'name': 'Somebody Else'})
        theirs = self.env['hr.payroll.adjustment'].create({
            'employee_id': other.id, 'type_id': self.fine.id, 'amount': 20.0, 'date_start': date(2026, 8, 1)})
        theirs.with_user(self.officer).action_confirm()
        seen = self.env['hr.payroll.adjustment'].with_user(self.employee_user).search([])
        self.assertEqual(seen, running, 'the running ones, not the drafts, nor those of others')
        self.assertTrue(running.with_user(self.employee_user).line_ids)
        with self.assertRaises(AccessError):
            draft.with_user(self.employee_user).read(['amount'])
