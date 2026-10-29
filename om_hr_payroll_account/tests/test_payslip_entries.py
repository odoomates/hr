# -*- coding: utf-8 -*-

from odoo.fields import Date
from odoo.tests.common import TransactionCase


class TestPayslipEntries(TransactionCase):

    def setUp(self):
        super(TestPayslipEntries, self).setUp()
        self.expense_account = self.env['account.account'].create({
            'name': 'Payroll Salaries', 'code': 'OMPAYEXP',
            'user_type_id': self.env.ref('account.data_account_type_expenses').id,
        })
        self.payable_account = self.env['account.account'].create({
            'name': 'Payroll Salaries Payable', 'code': 'OMPAYPAY', 'reconcile': True,
            'user_type_id': self.env.ref('account.data_account_type_payable').id,
        })
        self.journal = self.env['account.journal'].create({
            'name': 'Payroll Salaries', 'code': 'OMPAY', 'type': 'general',
        })
        self.employee = self.env['hr.employee'].create({
            'name': 'Payroll Employee',
            'address_home_id': self.env['res.partner'].create({'name': 'Payroll Employee'}).id,
        })
        self.basic_rule = self.env['hr.salary.rule'].create({
            'name': 'Basic Salary', 'code': 'BASIC', 'sequence': 1,
            'category_id': self.env.ref('om_hr_payroll.BASIC').id,
            'amount_select': 'code', 'amount_python_compute': 'result = contract.wage',
            'account_debit': self.expense_account.id,
        })
        self.net_rule = self.env['hr.salary.rule'].create({
            'name': 'Net Salary', 'code': 'NET', 'sequence': 200,
            'category_id': self.env.ref('om_hr_payroll.NET').id,
            'amount_select': 'code', 'amount_python_compute': 'result = categories.BASIC + categories.DED',
            'account_credit': self.payable_account.id,
        })
        self.structure = self.env['hr.payroll.structure'].create({
            'name': 'Payroll Test Structure', 'code': 'PTS', 'parent_id': False,
            'rule_ids': [(6, 0, (self.basic_rule | self.net_rule).ids)],
        })
        self.contract = self.env['hr.contract'].create({
            'name': 'Contract of Payroll Employee',
            'employee_id': self.employee.id,
            'date_start': Date.to_date('2020-01-01'),
            'wage': 5000.0,
            'struct_id': self.structure.id,
            'journal_id': self.journal.id,
        })

    def _new_payslip(self):
        return self.env['hr.payslip'].create({
            'name': 'Payslip of Payroll Employee',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'struct_id': self.structure.id,
            'journal_id': self.journal.id,
            'date_from': Date.to_date('2020-03-01'),
            'date_to': Date.to_date('2020-03-31'),
        })

    def test_set_back_to_draft_removes_entry(self):
        """ Set back to draft and confirmed again, the payslip posts one entry, not a second one. """
        payslip = self._new_payslip()
        payslip.action_payslip_done()
        move = payslip.move_id
        self.assertEqual(move.state, 'posted')
        payslip.action_payslip_draft()
        self.assertEqual(payslip.state, 'draft')
        self.assertFalse(move.exists())
        self.assertFalse(payslip.move_id)

        payslip.action_payslip_done()
        self.assertEqual(payslip.move_id.state, 'posted')
        self.assertEqual(self.env['account.move'].search_count([('ref', '=', payslip.number)]), 1)

    def test_payslip_without_amounts_posts_no_entry(self):
        """ Nothing to post: the payslip is confirmed without an entry, as an empty one cannot be posted. """
        self.contract.wage = 0.0
        payslip = self._new_payslip()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')
        self.assertFalse(payslip.move_id)

    def test_contract_analytic_account(self):
        """ The journal items take the analytic account of the contract when the rule has none. """
        contract_analytic = self.env['account.analytic.account'].create({'name': 'Contract Analytic'})
        rule_analytic = self.env['account.analytic.account'].create({'name': 'Rule Analytic'})
        self.contract.analytic_account_id = contract_analytic
        payslip = self._new_payslip()
        payslip.action_payslip_done()
        expense = payslip.move_id.line_ids.filtered(lambda line: line.account_id == self.expense_account)
        self.assertEqual(expense.analytic_account_id, contract_analytic)

        # the analytic account of the rule comes first
        self.basic_rule.analytic_account_id = rule_analytic
        payslip = self._new_payslip()
        payslip.action_payslip_done()
        expense = payslip.move_id.line_ids.filtered(lambda line: line.account_id == self.expense_account)
        self.assertEqual(expense.analytic_account_id, rule_analytic)

    def test_employee_is_the_partner_of_receivable_items(self):
        """ A salary advance recovered is reconciled per employee: its receivable item carries the employee. """
        advances = self.env['account.account'].create({
            'name': 'Salary Advances', 'code': 'OMPAYADV', 'reconcile': True,
            'user_type_id': self.env.ref('account.data_account_type_receivable').id,
        })
        self.structure.rule_ids = [(4, self.env['hr.salary.rule'].create({
            'name': 'Advance Recovered', 'code': 'ADVREC', 'sequence': 160,
            'category_id': self.env.ref('om_hr_payroll.DED').id, 'amount_select': 'fix', 'amount_fix': -500.0,
            # a deduction, so a negative amount: the debit account is credited with what is recovered
            'account_debit': advances.id,
        }).id)]
        payslip = self._new_payslip()
        payslip.action_payslip_done()
        lines = payslip.move_id.line_ids
        advance = lines.filtered(lambda line: line.account_id == advances)
        self.assertEqual(advance.credit, 500.0)
        self.assertEqual(advance.partner_id, self.employee.address_home_id)
        # an account that is neither receivable nor payable is not the employee's
        self.assertFalse(lines.filtered(lambda line: line.account_id == self.expense_account).partner_id)
