from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestPayrollExportMultiCompany(TransactionCase):
    """ The bank file of the payslips of a company is kept in that company, with a layout it may use. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env['res.company'].create({'name': 'Export Company B'})
        if 'journal_id' in cls.env['hr.payslip']._fields:
            cls.env['account.journal'].create({
                'name': 'Salaries B', 'code': 'SALXB', 'type': 'general', 'company_id': cls.company_b.id})
        rules = cls.env.ref('om_hr_payroll.hr_rule_basic') | cls.env.ref('om_hr_payroll.hr_rule_net')
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Shared Export', 'code': 'EXPMC', 'parent_id': False, 'company_id': False,
            'rule_ids': [Command.set(rules.ids)]})
        cls.layout = cls.env.ref('om_hr_payroll_export.layout_bank_transfer_csv')
        cls.layout_a = cls.layout.copy({'name': 'Bank File of A', 'company_id': cls.env.company.id})
        employee = cls.env['hr.employee'].with_company(cls.company_b).create({
            'name': 'Payee of B', 'company_id': cls.company_b.id, 'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1), 'wage': 3000.0, 'struct_id': cls.structure.id})
        employee.bank_account_ids = cls.env['res.partner.bank'].create({
            'account_number': 'MC-EXPORT-B', 'partner_id': employee.work_contact_id.id, 'allow_out_payment': True})
        with Form(cls.env['hr.payslip'].with_company(cls.company_b)) as form:
            form.employee_id = employee
            form.date_from = date(2026, 6, 1)
            form.date_to = date(2026, 6, 30)
        cls.payslip_b = form.record
        cls.payslip_b.compute_sheet()
        cls.payslip_b.write({'state': 'done', 'number': 'SLIP/MC/%s' % cls.payslip_b.id})

    def wizard(self, layout=None):
        action = self.payslip_b.with_company(self.company_b).action_export_bank_file()
        with Form(self.env[action['res_model']].with_company(self.company_b).with_context(**action['context'])) \
                as form:
            if layout:
                form.layout_id = layout
        return form.record

    def test_export_kept_in_the_company_of_the_payslips(self):
        self.wizard(self.layout).action_download()
        export = self.env['file.export'].search([('res_ids', 'ilike', str(self.payslip_b.id))], order='id desc',
                                                limit=1)
        self.assertEqual(export.company_id, self.company_b)
        user_a = new_test_user(self.env, 'om_mc_export_user', groups='base.group_user',
                               company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)])
        self.assertFalse(self.env['file.export'].with_user(user_a).search([('id', '=', export.id)]))

    def test_no_layout_of_another_company(self):
        with self.assertRaises(UserError):
            self.wizard(self.layout_a).action_download()

    def test_default_layout_of_the_company_of_the_payslips(self):
        # with both companies allowed, the layout of company A is never offered for the payslips of company B
        action = self.payslip_b.with_context(allowed_company_ids=[self.env.company.id, self.company_b.id]) \
            .action_export_bank_file()
        self.assertEqual(action['context']['default_layout_id'], self.layout.id)
        layout_b = self.layout.copy({'name': 'Bank File of B', 'company_id': self.company_b.id})
        action = self.payslip_b.with_context(allowed_company_ids=[self.env.company.id, self.company_b.id]) \
            .action_export_bank_file()
        self.assertEqual(action['context']['default_layout_id'], layout_b.id, 'the layout of its own company first')
