# -*- coding: utf-8 -*-

from odoo.fields import Date
from odoo.tests.common import TransactionCase


class TestPayslipComputation(TransactionCase):

    def setUp(self):
        super(TestPayslipComputation, self).setUp()
        self.employee = self.env['hr.employee'].create({'name': 'Payroll Employee'})
        self.basic_rule = self.env['hr.salary.rule'].create({
            'name': 'Basic Salary',
            'code': 'BASIC',
            'sequence': 1,
            'category_id': self.env.ref('om_hr_payroll.BASIC').id,
            'amount_select': 'code',
            'amount_python_compute': 'result = contract.wage',
        })
        self.structure = self.env['hr.payroll.structure'].create({
            'name': 'Payroll Test Structure',
            'code': 'PTS',
            'parent_id': False,
            'rule_ids': [(6, 0, self.basic_rule.ids)],
        })
        self.contract = self.env['hr.contract'].create({
            'name': 'Contract of Payroll Employee',
            'employee_id': self.employee.id,
            'date_start': Date.to_date('2020-01-01'),
            'wage': 5000.0,
            'struct_id': self.structure.id,
        })

    def _compute_payslip(self):
        payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Payroll Employee',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'struct_id': self.structure.id,
            'date_from': Date.to_date('2020-03-01'),
            'date_to': Date.to_date('2020-03-31'),
        })
        payslip.compute_sheet()
        return payslip

    def _add_rule(self, **values):
        rule = self.env['hr.salary.rule'].create(dict({
            'category_id': self.env.ref('om_hr_payroll.ALW').id,
            'amount_select': 'fix',
        }, **values))
        self.structure.rule_ids = [(4, rule.id)]
        return rule

    def test_python_rule_zero_quantity_and_rate(self):
        """ A python rule returning a quantity or a rate of 0 pays nothing, not the default 1 or 100%. """
        self._add_rule(name='No Quantity', code='NOQTY', sequence=10, amount_select='code',
                       amount_python_compute='result = 1000.0\nresult_qty = 0.0')
        self._add_rule(name='No Rate', code='NORATE', sequence=11, amount_select='code',
                       amount_python_compute='result = 1000.0\nresult_rate = 0.0')
        lines = self._compute_payslip().line_ids
        no_quantity = lines.filtered(lambda line: line.code == 'NOQTY')
        self.assertEqual(no_quantity.quantity, 0.0)
        self.assertEqual(no_quantity.total, 0.0)
        no_rate = lines.filtered(lambda line: line.code == 'NORATE')
        self.assertEqual(no_rate.rate, 0.0)
        self.assertEqual(no_rate.total, 0.0)

    def test_credit_note_stored_as_false(self):
        """ A payslip or a batch created without the credit note flag stores False, not NULL. """
        payslip = self._compute_payslip()
        run = self.env['hr.payslip.run'].create({'name': 'Payroll Test Batch'})
        payslip.flush()
        run.flush()
        self.env.cr.execute("SELECT credit_note FROM hr_payslip WHERE id = %s", (payslip.id,))
        self.assertIs(self.env.cr.fetchone()[0], False)
        self.env.cr.execute("SELECT credit_note FROM hr_payslip_run WHERE id = %s", (run.id,))
        self.assertIs(self.env.cr.fetchone()[0], False)

    def test_child_rule_follows_its_parent_whatever_the_sequence(self):
        """ A child rule computed before its parent applies only where its parent does. """
        parent = self._add_rule(name='Parent', code='PARENT', sequence=20, amount_fix=100.0,
                                condition_select='python', condition_python='result = contract.wage > 6000')
        self.env['hr.salary.rule'].create({
            'name': 'Child', 'code': 'CHILD', 'sequence': 10, 'parent_rule_id': parent.id,
            'category_id': self.env.ref('om_hr_payroll.ALW').id, 'amount_select': 'fix', 'amount_fix': 50.0,
        })
        codes = self._compute_payslip().line_ids.mapped('code')
        self.assertNotIn('PARENT', codes)
        self.assertNotIn('CHILD', codes)

        # where the parent applies, so does the child
        self.contract.wage = 7000.0
        codes = self._compute_payslip().line_ids.mapped('code')
        self.assertIn('PARENT', codes)
        self.assertIn('CHILD', codes)

    def test_sum_of_the_confirmed_payslips(self):
        """ payslip.sum() adds the confirmed payslips, the ones stored without the credit note flag included, and
        takes the refunds off. """
        self._add_rule(name='Paid Before', code='PAIDBEFORE', sequence=20, amount_select='code',
                       amount_python_compute="result = payslip.sum('BASIC', '2020-01-01', '2020-12-31')")
        march = self._compute_payslip()
        march.write({'state': 'done'})
        march.flush()
        # as stored by an import or a script writing the table
        self.env.cr.execute("UPDATE hr_payslip SET credit_note = NULL WHERE id = %s", (march.id,))
        march.invalidate_cache()

        april = self.env['hr.payslip'].create({
            'name': 'April Payslip of Payroll Employee',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'struct_id': self.structure.id,
            'date_from': Date.to_date('2020-04-01'),
            'date_to': Date.to_date('2020-04-30'),
        })
        april.compute_sheet()
        paid_before = april.line_ids.filtered(lambda line: line.code == 'PAIDBEFORE')
        self.assertEqual(paid_before.total, 5000.0)

        refund = march.copy({'credit_note': True, 'name': 'Refund of March'})
        refund.compute_sheet()
        refund.write({'state': 'done'})
        april.compute_sheet()
        paid_before = april.line_ids.filtered(lambda line: line.code == 'PAIDBEFORE')
        self.assertEqual(paid_before.total, 0.0)
