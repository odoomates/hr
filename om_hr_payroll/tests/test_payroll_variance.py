from datetime import date

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPayrollVariance(TransactionCase):
    """ Mark as Done of a batch lists first the payslips changing much from the last confirmed one. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env['resource.calendar'].create({'name': 'Variance 40h'})
        rules = cls.env['hr.salary.rule'].create([{
            'name': 'Basic', 'code': 'BASIC', 'sequence': 1, 'category_id': cls.env.ref('om_hr_payroll.BASIC').id,
            'amount_select': 'code', 'amount_python_compute': 'result = contract.wage',
        }, {
            'name': 'Bonus', 'code': 'BONUS', 'sequence': 4, 'category_id': cls.env.ref('om_hr_payroll.ALW').id,
            'amount_select': 'code', 'amount_python_compute': 'result = inputs.BONUS and inputs.BONUS.amount',
            'input_ids': [Command.create({'name': 'Bonus', 'code': 'BONUS'})],
        }])
        rules |= cls.env.ref('om_hr_payroll.hr_rule_taxable') | cls.env.ref('om_hr_payroll.hr_rule_net')
        if 'account_debit' in rules._fields:
            # payroll accounting is installed: a confirmed payslip is posted, so the rules need accounts
            cls.env['account.journal'].create({'name': 'Payroll Variance', 'code': 'PAYVA', 'type': 'general'})
            rules.write({
                'account_debit': cls.env['account.account'].create({
                    'name': 'Payroll Expense Variance', 'code': 'PAYEXPVA', 'account_type': 'expense'}).id,
                'account_credit': cls.env['account.account'].create({
                    'name': 'Payroll Payable Variance', 'code': 'PAYPAYVA', 'account_type': 'liability_current'}).id,
            })
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Variance Structure', 'code': 'VARTEST', 'parent_id': False, 'rule_ids': [Command.set(rules.ids)],
        })
        cls.steady = cls._create_employee('Steady Employee')
        cls.raised = cls._create_employee('Raised Employee')
        july = cls._create_run('July', date(2026, 7, 1), date(2026, 7, 31), cls.steady | cls.raised)
        july.done_payslip_run()
        cls.raised.version_id.wage = 1200.0
        cls.env.company.om_payroll_variance_threshold = 10.0

    @classmethod
    def _create_employee(cls, name):
        return cls.env['hr.employee'].create({
            'name': name, 'resource_calendar_id': cls.calendar.id, 'tz': 'UTC',
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1),
            'wage': 1000.0, 'struct_id': cls.structure.id,
        })

    @classmethod
    def _create_run(cls, name, date_start, date_end, employees):
        run = cls.env['hr.payslip.run'].create({'name': name, 'date_start': date_start, 'date_end': date_end})
        wizard = cls.env['hr.payslip.employees'].create({'employee_ids': [Command.set(employees.ids)]})
        wizard.with_context(active_id=run.id).compute_sheet()
        return run

    def test_variance_listed_then_confirmed(self):
        newcomer = self._create_employee('New Employee')
        run = self._create_run('August', date(2026, 8, 1), date(2026, 8, 31), self.steady | self.raised | newcomer)

        action = run.action_done_payslip_run()
        self.assertEqual(action['res_model'], 'hr.payslip.run.variance')
        self.assertEqual(run.state, 'draft', 'Nothing is confirmed before the check is answered')
        check = self.env['hr.payslip.run.variance'].browse(action['res_id'])
        lines = {line.employee_id: line for line in check.line_ids}
        self.assertEqual(set(lines), {self.raised, newcomer}, 'The steady pay is not listed')

        raised = lines[self.raised]
        self.assertEqual(raised.reason, 'variance')
        self.assertEqual((raised.previous_net, raised.net), (1000.0, 1200.0))
        self.assertAlmostEqual(raised.net_change, 0.2)
        self.assertEqual((raised.top_rule, raised.top_difference), ('Basic', 200.0))
        self.assertEqual(raised.previous_payslip_id.date_from, date(2026, 7, 1))
        self.assertEqual(lines[newcomer].reason, 'first')
        self.assertEqual(lines[newcomer].net, 1000.0)

        check.action_confirm()
        self.assertEqual(run.state, 'done')
        self.assertEqual(set(run.slip_ids.mapped('state')), {'done'})
        self.assertTrue(any('Raised Employee' in message.body for message in run.message_ids))

    def test_change_below_threshold(self):
        self.raised.version_id.wage = 1050.0
        run = self._create_run('August', date(2026, 8, 1), date(2026, 8, 31), self.steady | self.raised)
        run.action_done_payslip_run()
        self.assertEqual(run.state, 'done', 'A change of 5% is below the threshold of 10%')

    def test_input_changes_after_compute(self):
        # the check computes the payslips again, as Mark as Done does: a bonus added since is seen
        run = self._create_run('August', date(2026, 8, 1), date(2026, 8, 31), self.steady)
        run.slip_ids.input_line_ids.filtered(lambda line: line.code == 'BONUS').amount = 500.0
        action = run.action_done_payslip_run()
        line = self.env['hr.payslip.run.variance'].browse(action['res_id']).line_ids
        self.assertEqual((line.employee_id, line.top_rule, line.top_difference), (self.steady, 'Bonus', 500.0))

    def test_check_turned_off(self):
        self.env.company.om_payroll_variance_threshold = 0.0
        run = self._create_run('August', date(2026, 8, 1), date(2026, 8, 31), self.steady | self.raised)
        run.action_done_payslip_run()
        self.assertEqual(run.state, 'done')

    def test_refund_not_compared(self):
        # the refund of the last payslip pays minus its amounts: the payslip itself is compared with
        july = self.env['hr.payslip'].search([('employee_id', '=', self.steady.id), ('state', '=', 'done')])
        july.refund_sheet()
        self.assertTrue(self.env['hr.payslip'].search([('employee_id', '=', self.steady.id), ('credit_note', '=', True)]))
        run = self._create_run('August', date(2026, 8, 1), date(2026, 8, 31), self.steady)
        run.action_done_payslip_run()
        self.assertEqual(run.state, 'done', 'The July payslip is compared with, not its refund')
