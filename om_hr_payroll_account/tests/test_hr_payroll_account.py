from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestHrPayrollAccount(AccountTestInvoicingCommon):
    """ A payslip confirmed posts its journal entry, from the accounts of its salary rules. """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.journal = cls.company_data['default_journal_misc']
        cls.journal.default_account_id = cls.company_data['default_account_expense']
        cls.employee = cls.env['hr.employee'].create({'name': 'John', 'company_id': cls.env.company.id})
        rules = cls.env['hr.salary.rule'].search([('code', 'in', ('BASIC', 'HRA', 'CA', 'PT', 'PF'))])
        rules.write({
            'account_debit': cls.company_data['default_account_expense'].id,
            'account_credit': cls.company_data['default_account_payable'].id,
        })
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Software Developer',
            'code': 'SD',
            'company_id': cls.env.company.id,
            'parent_id': cls.env.ref('om_hr_payroll.structure_base').id,
            'rule_ids': [(6, 0, rules.ids)],
        })
        cls.date_from = date.today().replace(day=1)
        cls.date_to = cls.date_from + relativedelta(months=1, days=-1)
        cls.contract = cls.env['hr.contract'].create({
            'name': 'Contract for John',
            'employee_id': cls.employee.id,
            'wage': 5000.0,
            'date_start': cls.date_from,
            'state': 'open',
            'type_id': cls.env.ref('om_hr_payroll.hr_contract_type_emp').id,
            'struct_id': cls.structure.id,
            'journal_id': cls.journal.id,
            'company_id': cls.env.company.id,
        })

    def test_00_hr_payslip(self):
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'journal_id': self.journal.id,
        })
        values = payslip.onchange_employee_id(self.date_from, self.date_to, self.employee.id)['value']
        payslip.write({
            'contract_id': values['contract_id'],
            'struct_id': values['struct_id'],
            'worked_days_line_ids': [(0, 0, line) for line in values['worked_days_line_ids']],
            'input_line_ids': [(0, 0, line) for line in values['input_line_ids']],
        })
        self.assertEqual(payslip.contract_id, self.contract)
        self.assertEqual(payslip.state, 'draft')

        payslip.compute_sheet()
        self.assertTrue(payslip.line_ids)

        # cancelled, then back to draft
        payslip.action_payslip_cancel()
        self.assertEqual(payslip.state, 'cancel')
        payslip.action_payslip_draft()

        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')
        self.assertTrue(payslip.move_id, "The journal entry of the payslip is not created")
        self.assertEqual(payslip.move_id.journal_id, self.journal)
        self.assertAlmostEqual(sum(payslip.move_id.line_ids.mapped('debit')),
                               sum(payslip.move_id.line_ids.mapped('credit')))

    def _new_payslip(self):
        payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'contract_id': self.contract.id,
            'struct_id': self.structure.id,
            'journal_id': self.journal.id,
        })
        return payslip

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
        self.structure.rule_ids = self.structure.rule_ids.filtered(lambda rule: rule.code == 'HRA')
        self.contract.wage = 0.0
        payslip = self._new_payslip()
        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')
        self.assertTrue(payslip.line_ids)
        self.assertFalse(payslip.move_id)

    def test_contract_analytic_account(self):
        """ The journal items take the analytic account of the contract when the rule has none. """
        expense = self.company_data['default_account_expense']
        contract_analytic, rule_analytic = self.env['account.analytic.account'].create([
            {'name': 'Contract Analytic'},
            {'name': 'Rule Analytic'},
        ])
        self.contract.analytic_account_id = contract_analytic
        payslip = self._new_payslip()
        payslip.action_payslip_done()
        basic = payslip.move_id.line_ids.filtered(
            lambda line: line.account_id == expense and line.name == 'Basic Salary')
        self.assertEqual(len(basic), 1)
        self.assertEqual(basic.analytic_account_id, contract_analytic)

        # the analytic account of the rule comes first
        basic_rule = payslip.line_ids.filtered(lambda line: line.code == 'BASIC').salary_rule_id
        basic_rule.analytic_account_id = rule_analytic
        payslip = self._new_payslip()
        payslip.action_payslip_done()
        basic = payslip.move_id.line_ids.filtered(
            lambda line: line.account_id == expense and line.name == 'Basic Salary')
        self.assertEqual(basic.analytic_account_id, rule_analytic)

    def test_employee_is_the_partner_of_receivable_items(self):
        """ A salary advance recovered is reconciled per employee: its receivable item carries the employee. """
        partner = self.env['res.partner'].create({'name': 'John'})
        self.employee.address_home_id = partner
        receivable = self.company_data['default_account_receivable']
        self.structure.rule_ids = [(4, self.env['hr.salary.rule'].create({
            'name': 'Advance Recovered', 'code': 'ADVREC', 'sequence': 160,
            'category_id': self.env.ref('om_hr_payroll.DED').id, 'amount_select': 'fix', 'amount_fix': -500.0,
            # a deduction, so a negative amount: the debit account is credited with what is recovered
            'account_debit': receivable.id,
            'account_credit': self.company_data['default_account_payable'].id,
        }).id)]
        payslip = self._new_payslip()
        payslip.action_payslip_done()
        lines = payslip.move_id.line_ids
        advance = lines.filtered(lambda line: line.account_id == receivable)
        self.assertEqual(advance.balance, -500.0)
        self.assertEqual(advance.partner_id, partner)
        # an account that is neither receivable nor payable is not the employee's
        self.assertFalse(lines.filtered(
            lambda line: line.account_id == self.company_data['default_account_expense']).partner_id)
