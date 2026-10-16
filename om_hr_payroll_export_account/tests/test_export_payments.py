from datetime import date

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestExportPayments(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [Command.link(cls.env.ref('om_hr_payroll.group_hr_payroll_manager').id)]
        salary_payable = cls.env['account.account'].create({
            'name': 'Salaries to Pay', 'code': 'SALEXPPAY', 'account_type': 'liability_payable', 'reconcile': True})
        clearing = cls.env['account.account'].create({
            'name': 'Gross Salaries', 'code': 'SALEXPGROSS', 'account_type': 'liability_current'})
        basic = cls.env['hr.salary.rule'].create({
            'name': 'Basic', 'code': 'BASIC', 'sequence': 1, 'category_id': cls.env.ref('om_hr_payroll.BASIC').id,
            'amount_select': 'code', 'amount_python_compute': 'result = contract.wage',
            'account_debit': cls.company_data['default_account_expense'].id, 'account_credit': clearing.id})
        net = cls.env.ref('om_hr_payroll.hr_rule_net')
        net.write({'account_debit': clearing.id, 'account_credit': salary_payable.id})
        structure = cls.env['hr.payroll.structure'].create({
            'name': 'Exported Structure', 'code': 'EXPPAY', 'parent_id': False,
            'rule_ids': [Command.set((basic | net).ids)], 'company_id': cls.env.company.id})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Exported Employee', 'tz': 'UTC', 'company_id': cls.env.company.id,
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1), 'wage': 2500.0,
            'struct_id': structure.id})
        cls.employee.bank_account_ids = cls.env['res.partner.bank'].create({
            'account_number': 'EXP-ACC-1', 'partner_id': cls.employee.work_contact_id.id,
            'allow_out_payment': True})

    def test_export_registers_the_payments(self):
        with Form(self.env['hr.payslip']) as form:
            form.employee_id = self.employee
            form.date_from = date(2026, 8, 1)
            form.date_to = date(2026, 8, 31)
            form.journal_id = self.company_data['default_journal_misc']
        payslip = form.record
        payslip.action_payslip_done()
        self.assertEqual(payslip.payment_state, 'not_paid')

        action = payslip.action_export_bank_file()
        with Form(self.env[action['res_model']].with_context(action['context'])) as wizard_form:
            wizard_form.register_payment = True
            wizard_form.journal_id = self.company_data['default_journal_bank']
            wizard_form.payment_date = date(2026, 9, 1)
        wizard_form.record.action_download()

        self.assertTrue(payslip.exported)
        self.assertEqual(payslip.payment_ids.amount, 2500.0)
        self.assertEqual(payslip.payment_ids.date, date(2026, 9, 1))
        self.assertIn(payslip.payment_state, ('in_payment', 'paid'))

    def test_without_the_option_nothing_is_paid(self):
        with Form(self.env['hr.payslip']) as form:
            form.employee_id = self.employee
            form.date_from = date(2026, 8, 1)
            form.date_to = date(2026, 8, 31)
            form.journal_id = self.company_data['default_journal_misc']
        payslip = form.record
        payslip.action_payslip_done()
        action = payslip.action_export_bank_file()
        Form(self.env[action['res_model']].with_context(action['context'])).save().action_download()
        self.assertFalse(payslip.payment_ids)
