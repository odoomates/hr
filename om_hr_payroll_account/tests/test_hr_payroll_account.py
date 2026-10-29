# -*- coding: utf-8 -*-

from odoo.addons.om_hr_payroll.tests.common import TestPayslipBase


class TestHrPayrollAccount(TestPayslipBase):

    def setUp(self):
        super(TestHrPayrollAccount, self).setUp()
        expense_account = self.env['account.account'].create({
            'name': 'Salary Expenses', 'code': 'OMSALEXP',
            'user_type_id': self.env.ref('account.data_account_type_expenses').id,
        })
        payable_account = self.env['account.account'].create({
            'name': 'Salaries Payable', 'code': 'OMSALPAY', 'reconcile': True,
            'user_type_id': self.env.ref('account.data_account_type_payable').id,
        })
        self.journal = self.env['account.journal'].create({
            'name': 'Salaries', 'code': 'OMSAL', 'type': 'general',
            'default_account_id': expense_account.id,
        })
        self.env.ref('om_hr_payroll.hr_rule_basic').account_debit = expense_account
        self.env.ref('om_hr_payroll.hr_rule_net').account_credit = payable_account
        self.richard_emp.address_home_id = self.env['res.partner'].create({'name': 'Richard'})
        self.richard_contract.journal_id = self.journal

    def test_00_hr_payslip(self):
        """ The process of a payslip: computed, cancelled, set back to draft and confirmed, with its entry. """
        payslip = self._new_payslip(journal_id=self.journal.id)
        payslip.input_line_ids.write({'amount': 5.0})
        self.assertEqual(payslip.state, 'draft')

        payslip.compute_sheet()
        payslip.action_payslip_cancel()
        self.assertEqual(payslip.state, 'cancel')
        payslip.action_payslip_draft()

        payslip.action_payslip_done()
        self.assertEqual(payslip.state, 'done')
        self.assertTrue(payslip.move_id, 'Accounting Entries has not been created')
        self.assertEqual(payslip.move_id.state, 'posted')
        self.assertEqual(payslip.move_id.journal_id, self.journal)
