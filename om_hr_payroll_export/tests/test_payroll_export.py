from datetime import date

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPayrollExport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        rules = cls.env.ref('om_hr_payroll.hr_rule_basic') | cls.env.ref('om_hr_payroll.hr_rule_net')
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Export Structure', 'code': 'EXPTEST', 'parent_id': False, 'rule_ids': [Command.set(rules.ids)]})
        cls.employee = cls.new_employee('Split Payee')
        partner = cls.employee.work_contact_id
        Bank = cls.env['res.partner.bank']
        cls.main_account = Bank.create({'account_number': 'AE070331234567890123456', 'partner_id': partner.id,
                                        'allow_out_payment': True})
        cls.savings = Bank.create({'account_number': 'AE460260001015333439101', 'partner_id': partner.id,
                                   'allow_out_payment': True})
        cls.employee.bank_account_ids = cls.main_account | cls.savings
        cls.employee.salary_distribution = {
            str(cls.main_account.id): {'sequence': 1, 'amount': 60.0, 'amount_is_percentage': True},
            str(cls.savings.id): {'sequence': 2, 'amount': 40.0, 'amount_is_percentage': True},
        }
        cls.layout = cls.env.ref('om_hr_payroll_export.layout_bank_transfer_csv')

    @classmethod
    def new_employee(cls, name):
        return cls.env['hr.employee'].create({
            'name': name, 'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1),
            'wage': 3000.0, 'struct_id': cls.structure.id})

    def confirmed_payslip(self, employee):
        with Form(self.env['hr.payslip']) as form:
            form.employee_id = employee
            form.date_from = date(2026, 6, 1)
            form.date_to = date(2026, 6, 30)
        payslip = form.record
        payslip.compute_sheet()
        payslip.write({'state': 'done', 'number': 'SLIP/%s' % payslip.id})
        return payslip

    def export(self, payslips):
        action = payslips.action_export_bank_file()
        return Form(self.env[action['res_model']].with_context(**action['context'])).save()

    def test_net_split_by_salary_distribution(self):
        payslip = self.confirmed_payslip(self.employee)
        wizard = self.export(payslip)
        self.assertEqual(wizard.layout_id, self.layout)
        self.assertEqual((wizard.line_count, wizard.total), (2, 3000.0))
        self.assertFalse(wizard.has_problems, wizard.problems)
        content = self.layout._render(payslip)['content'].decode()
        self.assertIn('Split Payee,AE070331234567890123456,Split Payee,,,1800.00', content)
        self.assertIn('Split Payee,AE460260001015333439101,Split Payee,,,1200.00', content)

        wizard.action_download()
        self.assertTrue(payslip.exported)
        self.assertIn('already in', self.export(payslip).problems)

    def test_problems(self):
        no_bank = self.confirmed_payslip(self.new_employee('No Bank'))
        untrusted_employee = self.new_employee('Untrusted')
        untrusted_employee.bank_account_ids = self.env['res.partner.bank'].create({
            'account_number': 'UNTRUSTED-1', 'partner_id': untrusted_employee.work_contact_id.id,
            'allow_out_payment': False})
        untrusted = self.confirmed_payslip(untrusted_employee)
        problems = self.export(no_bank | untrusted).problems
        self.assertIn('No Bank has no bank account', problems)
        self.assertIn('Account Number: empty', problems)
        self.assertIn('UNTRUSTED-1 is not trusted', problems)

    def test_only_confirmed_payslips(self):
        payslip = self.confirmed_payslip(self.employee)
        draft = payslip.copy({'state': 'draft'})
        self.assertEqual(len(self.layout._get_lines(payslip | draft)), 2, 'the draft is left out')

    def test_payslip_lines_in_columns(self):
        layout = self.env['file.layout'].create({
            'name': 'WPS', 'model_id': self.env['ir.model']._get_id('hr.payslip'), 'file_format': 'fixed',
            'line_ending': 'lf', 'column_ids': [
                (0, 0, {'name': 'Basic', 'expression': "line('BASIC')", 'value_type': 'decimal',
                        'implied_decimals': True, 'width': 10, 'align': 'right', 'pad_char': '0'}),
                (0, 0, {'name': 'Days', 'expression': '(period_to - period_from).days + 1', 'value_type': 'integer',
                        'width': 2}),
            ]})
        content = layout._render(self.confirmed_payslip(self.employee))['content'].decode()
        self.assertEqual(content.splitlines()[0], '000030000030')
