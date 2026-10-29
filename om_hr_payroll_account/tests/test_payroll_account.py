from datetime import date

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestPayrollAccount(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [Command.link(cls.env.ref('hr.group_hr_manager').id),
                                  Command.link(cls.env.ref('om_hr_payroll.group_hr_payroll_manager').id)]
        cls.expense_account = cls.company_data['default_account_expense']
        cls.payable_account = cls.env['account.account'].create({
            'name': 'Salaries Payable', 'code': 'SALPAY', 'account_type': 'liability_current',
        })
        cls.journal = cls.company_data['default_journal_misc']
        rules = cls.env['hr.salary.rule'].create([{
            'name': 'Basic', 'code': 'BASIC', 'sequence': 1, 'category_id': cls.env.ref('om_hr_payroll.BASIC').id,
            'amount_select': 'code', 'amount_python_compute': 'result = contract.wage',
            'account_debit': cls.expense_account.id, 'account_credit': cls.payable_account.id,
        }, {
            'name': 'Tax', 'code': 'TAX', 'sequence': 150, 'category_id': cls.env.ref('om_hr_payroll.DED').id,
            'amount_select': 'percentage', 'amount_percentage': -10, 'amount_percentage_base': 'contract.wage',
        }])
        rules |= cls.env.ref('om_hr_payroll.hr_rule_net')
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Accounting Structure', 'code': 'ACC', 'parent_id': False, 'rule_ids': [Command.set(rules.ids)],
            'company_id': cls.env.company.id,
        })
        calendar = cls.env['resource.calendar'].create({'name': 'Payroll 40h', 'company_id': cls.env.company.id})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Accounted Employee', 'resource_calendar_id': calendar.id, 'tz': 'UTC',
            'company_id': cls.env.company.id,
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1), 'wage': 4000.0,
        })
        cls.employee.version_id.struct_id = cls.structure

    def _new_payslip(self):
        with Form(self.env['hr.payslip']) as payslip_form:
            payslip_form.employee_id = self.employee
            payslip_form.date_from = date(2026, 8, 1)
            payslip_form.date_to = date(2026, 8, 31)
            payslip_form.journal_id = self.journal
        return payslip_form.record

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
        self.employee.version_id.wage = 0.0
        payslip = self._new_payslip()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')
        self.assertFalse(payslip.move_id)

    def test_contract_analytic_account(self):
        """ The journal items take the analytic account of the contract when the rule has none. """
        plan = self.env['account.analytic.plan'].create({'name': 'Payroll Plan'})
        contract_analytic, rule_analytic = self.env['account.analytic.account'].create([
            {'name': 'Contract Analytic', 'plan_id': plan.id},
            {'name': 'Rule Analytic', 'plan_id': plan.id},
        ])
        self.employee.version_id.analytic_account_id = contract_analytic
        payslip = self._new_payslip()
        payslip.action_payslip_done()
        expense = payslip.move_id.line_ids.filtered(lambda line: line.account_id == self.expense_account)
        self.assertEqual(expense.analytic_distribution, {str(contract_analytic.id): 100})

        # the analytic account of the rule comes first
        self.structure.rule_ids.filtered(lambda rule: rule.code == 'BASIC').analytic_account_id = rule_analytic
        payslip = self._new_payslip()
        payslip.action_payslip_done()
        expense = payslip.move_id.line_ids.filtered(lambda line: line.account_id == self.expense_account)
        self.assertEqual(expense.analytic_distribution, {str(rule_analytic.id): 100})

    def test_employee_is_the_partner_of_receivable_items(self):
        """ A salary advance recovered is reconciled per employee: its receivable item carries the employee. """
        advances = self.env['account.account'].create({
            'name': 'Salary Advances', 'code': 'SALADV', 'account_type': 'asset_receivable', 'reconcile': True,
        })
        self.structure.rule_ids |= self.env['hr.salary.rule'].create({
            'name': 'Advance Recovered', 'code': 'ADVREC', 'sequence': 160,
            'category_id': self.env.ref('om_hr_payroll.DED').id, 'amount_select': 'fix', 'amount_fix': -500.0,
            # a deduction, so a negative amount: the debit account is credited with what is recovered
            'account_debit': advances.id, 'account_credit': self.payable_account.id,
        })
        payslip = self._new_payslip()
        payslip.action_payslip_done()
        lines = payslip.move_id.line_ids
        advance = lines.filtered(lambda line: line.account_id == advances)
        self.assertEqual(advance.balance, -500.0)
        self.assertTrue(self.employee.work_contact_id)
        self.assertEqual(advance.partner_id, self.employee.work_contact_id)
        # an account that is neither receivable nor payable is not the employee's
        self.assertFalse(lines.filtered(lambda line: line.account_id == self.expense_account).partner_id)
