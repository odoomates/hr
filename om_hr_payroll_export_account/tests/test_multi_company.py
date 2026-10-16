from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestExportPaymentsMultiCompany(AccountTestInvoicingCommon):
    """ The salaries of a company exported in a bank file are paid from a bank journal of that company. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids = [Command.link(cls.env.ref('om_hr_payroll.group_hr_payroll_manager').id)]
        cls.company_b_data = cls.setup_other_company(name='Export Payments B')
        cls.company_b = cls.company_b_data['company']
        cls.env.user.company_ids = [Command.link(cls.company_b.id)]
        Account = cls.env['account.account'].with_company(cls.company_b)
        clearing = Account.create({'name': 'Gross B', 'code': 'EXMCGROSS', 'account_type': 'liability_current'})
        payable = Account.create({'name': 'To Pay B', 'code': 'EXMCPAY', 'account_type': 'liability_payable',
                                  'reconcile': True})
        basic, net = cls.env.ref('om_hr_payroll.hr_rule_basic'), cls.env.ref('om_hr_payroll.hr_rule_net')
        basic.with_company(cls.company_b).write({
            'account_debit': cls.company_b_data['default_account_expense'].id, 'account_credit': clearing.id})
        net.with_company(cls.company_b).write({'account_debit': clearing.id, 'account_credit': payable.id})
        structure = cls.env['hr.payroll.structure'].create({
            'name': 'Shared Exported', 'code': 'EXPMCA', 'parent_id': False, 'company_id': False,
            'rule_ids': [Command.set((basic | net).ids)]})
        employee = cls.env['hr.employee'].with_company(cls.company_b).create({
            'name': 'Exported of B', 'tz': 'UTC', 'company_id': cls.company_b.id,
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1), 'wage': 2500.0,
            'struct_id': structure.id})
        employee.bank_account_ids = cls.env['res.partner.bank'].create({
            'account_number': 'EXP-MC-B', 'partner_id': employee.work_contact_id.id, 'allow_out_payment': True})
        with Form(cls.env['hr.payslip'].with_company(cls.company_b)) as form:
            form.employee_id = employee
            form.date_from = date(2026, 8, 1)
            form.date_to = date(2026, 8, 31)
        cls.payslip = form.record
        cls.payslip.compute_sheet()
        cls.payslip.action_payslip_done()

    def export(self, journal):
        action = self.payslip.with_company(self.company_b).action_export_bank_file()
        with Form(self.env[action['res_model']].with_company(self.company_b).with_context(**action['context'])) \
                as form:
            form.register_payment = True
            form.journal_id = journal
            form.payment_date = date(2026, 9, 1)
        form.record.action_download()

    def test_paid_from_a_journal_of_the_payslip_company(self):
        self.export(self.company_b_data['default_journal_bank'])
        payment = self.payslip.payment_ids
        self.assertEqual((payment.company_id, payment.journal_id), (self.company_b,
                                                                     self.company_b_data['default_journal_bank']))

    def test_no_journal_of_another_company(self):
        with self.assertRaises(UserError):
            self.export(self.company_data['default_journal_bank'])
        self.assertFalse(self.payslip.payment_ids)
