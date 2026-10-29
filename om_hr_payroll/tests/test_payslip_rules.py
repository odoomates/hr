# -*- coding: utf-8 -*-

from odoo.fields import Date

from odoo.addons.om_hr_payroll.tests.common import TestPayslipBase


class TestPayslipRules(TestPayslipBase):

    def setUp(self):
        super(TestPayslipRules, self).setUp()
        self.allowance = self.env.ref('om_hr_payroll.ALW')
        self.contract = self.env['hr.contract'].search([('employee_id', '=', self.richard_emp.id)])

    def _add_rules(self, values_list):
        rules = self.env['hr.salary.rule'].create(values_list)
        self.developer_pay_structure.write({'rule_ids': [(4, rule.id) for rule in rules]})
        return rules

    def _payslip(self):
        payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id,
        })
        payslip.compute_sheet()
        return payslip

    def _totals(self, payslip):
        return {line.code: line.total for line in payslip.line_ids}

    def test_python_rule_zero_quantity_and_rate(self):
        """ A quantity or a rate of 0 returned by a python rule pays nothing, it is not the default. """
        self._add_rules([{
            'name': 'No Hours', 'code': 'NOHOURS', 'sequence': 50, 'category_id': self.allowance.id,
            'amount_select': 'code', 'amount_python_compute': 'result = 100\nresult_qty = 0',
        }, {
            'name': 'No Rate', 'code': 'NORATE', 'sequence': 51, 'category_id': self.allowance.id,
            'amount_select': 'code', 'amount_python_compute': 'result = 100\nresult_rate = 0',
        }, {
            'name': 'Half', 'code': 'HALF', 'sequence': 52, 'category_id': self.allowance.id,
            'amount_select': 'code', 'amount_python_compute': 'result = 100\nresult_qty = 3\nresult_rate = 50',
        }])
        totals = self._totals(self._payslip())
        self.assertEqual(totals['NOHOURS'], 0.0)
        self.assertEqual(totals['NORATE'], 0.0)
        self.assertEqual(totals['HALF'], 150.0)

    def test_sum_counts_payslips_stored_without_credit_note(self):
        """ A payslip stored without the credit note flag is no refund: the sum of the rules adds it. """
        first = self._payslip()
        self.assertFalse(first.credit_note)
        self.assertEqual(self._totals(first)['HRA'], 2000.0)
        first.write({'state': 'done'})
        # as stored by an import or a script writing the table
        self.env['hr.payslip'].flush()
        self.env.cr.execute("UPDATE hr_payslip SET credit_note = NULL WHERE id = %s", (first.id,))
        self.env['hr.payslip'].invalidate_cache()

        self._add_rules({
            'name': 'Paid Before', 'code': 'PAIDBEFORE', 'sequence': 200, 'category_id': self.allowance.id,
            'amount_select': 'code',
            'amount_python_compute': "result = payslip.sum('HRA', '%s', '%s')" % (
                Date.to_string(first.date_from), Date.to_string(first.date_to)),
        })
        self.assertEqual(self._totals(self._payslip())['PAIDBEFORE'], 2000.0)

    def test_child_rule_follows_its_parent_whatever_the_sequence(self):
        """ A child rule computed before its parent still applies only where the parent does. """
        parent = self.env['hr.salary.rule'].create({
            'name': 'Senior', 'code': 'SENIOR', 'sequence': 60, 'category_id': self.allowance.id,
            'condition_select': 'python', 'condition_python': 'result = contract.wage > 5000',
            'amount_select': 'fix', 'amount_fix': 100.0,
        })
        self.env['hr.salary.rule'].create({
            'name': 'Senior Bonus', 'code': 'SENIORBONUS', 'sequence': 50, 'category_id': self.allowance.id,
            'parent_rule_id': parent.id, 'amount_select': 'fix', 'amount_fix': 50.0,
        })
        self.developer_pay_structure.write({'rule_ids': [(4, parent.id)]})
        totals = self._totals(self._payslip())
        self.assertNotIn('SENIOR', totals)
        self.assertNotIn('SENIORBONUS', totals)

        self.contract.wage = 6000.0
        totals = self._totals(self._payslip())
        self.assertEqual(totals['SENIOR'], 100.0)
        self.assertEqual(totals['SENIORBONUS'], 50.0)
