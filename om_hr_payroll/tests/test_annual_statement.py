from datetime import date

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestAnnualStatement(TransactionCase):
    """ The pay of a payroll year month by month, and the contributions stopping at a yearly ceiling. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env['resource.calendar'].create({'name': 'Statement 40h'})
        rules = cls.env['hr.salary.rule'].create([{
            'name': 'Basic', 'code': 'BASIC', 'sequence': 1, 'category_id': cls.env.ref('om_hr_payroll.BASIC').id,
            'amount_select': 'code', 'amount_python_compute': 'result = contract.wage',
        }, {
            # the base of a contribution capped at 2,500 a year, and the contribution of 10% on it
            'name': 'Social Security Base', 'code': 'SSBASE', 'sequence': 50, 'appears_on_payslip': False,
            'category_id': cls.env.ref('om_hr_payroll.COMP').id,
            'amount_select': 'code', 'amount_python_compute': "result = ytd.capped('SSBASE', categories.BASIC, 2500)",
        }, {
            'name': 'Social Security', 'code': 'SS', 'sequence': 60, 'category_id': cls.env.ref('om_hr_payroll.DED').id,
            'amount_select': 'code', 'amount_python_compute': 'result = -0.1 * SSBASE',
        }])
        rules |= cls.env.ref('om_hr_payroll.hr_rule_net')
        if 'account_debit' in rules._fields:
            # payroll accounting is installed: a confirmed payslip is posted, so the rules need accounts
            cls.env['account.journal'].create({'name': 'Payroll Statement', 'code': 'PAYST', 'type': 'general'})
            rules.write({
                'account_debit': cls.env['account.account'].create({
                    'name': 'Payroll Expense Statement', 'code': 'PAYEXPST', 'account_type': 'expense'}).id,
                'account_credit': cls.env['account.account'].create({
                    'name': 'Payroll Payable Statement', 'code': 'PAYPAYST', 'account_type': 'liability_current'}).id,
            })
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Statement Structure', 'code': 'STATTEST', 'parent_id': False,
            'rule_ids': [Command.set(rules.ids)],
        })
        cls.user = new_test_user(cls.env, login='statement_employee', groups='base.group_user')
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Statement Employee', 'resource_calendar_id': cls.calendar.id, 'tz': 'UTC',
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1),
            'wage': 1000.0, 'struct_id': cls.structure.id, 'user_id': cls.user.id,
        })
        cls.payslips = cls.env['hr.payslip']
        for month in (1, 2, 3, 4):
            cls.payslips |= cls._confirm(date(2026, month, 1))

    @classmethod
    def _confirm(cls, date_from):
        with Form(cls.env['hr.payslip']) as form:
            form.employee_id = cls.employee
            form.date_from = date_from
            form.date_to = date_from.replace(day=28)
        payslip = form.record
        payslip.action_payslip_done()
        return payslip

    @staticmethod
    def _total(payslip, code):
        return sum(payslip.line_ids.filtered(lambda line: line.code == code).mapped('total'))

    def test_capped_contribution(self):
        # 1,000 a month under a ceiling of 2,500 a year: 1,000, 1,000, then the 500 left, then nothing
        self.assertEqual([self._total(slip, 'SSBASE') for slip in self.payslips], [1000.0, 1000.0, 500.0, 0.0])
        self.assertEqual([self._total(slip, 'SS') for slip in self.payslips], [-100.0, -100.0, -50.0, 0.0])

    def test_statement_by_month(self):
        # the April payslip refunded: the refund is computed again, and nothing is left to contribute in April
        self.payslips[3].refund_sheet()
        statement = self.env['report.om_hr_payroll.report_annual_statement']._get_statement(self.employee, 2026)
        self.assertEqual((statement['date_from'], statement['date_to']), (date(2026, 1, 1), date(2026, 12, 31)))
        self.assertEqual([month for month, _label in statement['months']],
                         [date(2026, month, 1) for month in (1, 2, 3, 4)])
        rows = {row['code']: row for row in statement['rows']}
        self.assertNotIn('SSBASE', rows, 'A rule not shown on the payslips is not shown on the statement')
        self.assertEqual(list(rows), ['BASIC', 'SS', 'NET'], 'In the order of the rules')
        self.assertEqual(rows['BASIC']['amounts'][date(2026, 4, 1)], 0.0, 'The refund is taken back')
        self.assertEqual(rows['BASIC']['total'], 3000.0)
        self.assertEqual(rows['SS']['amounts'][date(2026, 3, 1)], -50.0)
        self.assertEqual(rows['NET']['total'], 3000.0 - 250.0)
        self.assertTrue(rows['NET']['net'])

        empty = self.env['report.om_hr_payroll.report_annual_statement']._get_statement(self.employee, 2025)
        self.assertFalse(empty['rows'])

    def test_print_from_wizard(self):
        wizard = self.env['hr.payslip.annual.statement'].with_context(
            active_model='hr.employee', active_ids=self.employee.ids).create({'year': 2026})
        self.assertEqual(wizard.employee_ids, self.employee)
        self.assertEqual((wizard.date_from, wizard.date_to), (date(2026, 1, 1), date(2026, 12, 31)))
        # a company without a document layout is asked to choose one before printing
        self.env.company.external_report_layout_id = self.env.ref('web.external_layout_standard')
        action = wizard.action_print()
        self.assertEqual((action['report_name'], action['data']), (
            'om_hr_payroll.report_annual_statement', {'year': 2026}))
        html, _type = self.env['ir.actions.report']._render_qweb_html(
            'om_hr_payroll.action_report_annual_statement', self.employee.ids, data={'year': 2026})
        self.assertIn('Statement Employee', html.decode())
        self.assertIn('Social Security', html.decode())

    def test_own_statement(self):
        pdf, name = self.env['hr.payslip'].with_user(self.user)._om_render_own_statement(2026)
        self.assertTrue(pdf)
        self.assertEqual(name, 'Annual Statement 2026.pdf')
        outsider = new_test_user(self.env, login='statement_outsider', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.env['hr.payslip'].with_user(outsider)._om_render_own_statement(2026)
