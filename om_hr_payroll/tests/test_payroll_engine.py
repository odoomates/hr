from datetime import date

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPayrollEngine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env['resource.calendar'].create({'name': 'Engine 40h'})
        rules = cls.env.ref('om_hr_payroll.hr_rule_basic') | cls.env.ref('om_hr_payroll.hr_rule_net')
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Engine Structure', 'code': 'ENGINETEST', 'parent_id': False,
            'rule_ids': [Command.set(rules.ids)],
        })

    def _employee(self, **values):
        employee = self.env['hr.employee'].create({
            'name': 'Engine Employee', 'resource_calendar_id': self.calendar.id, 'tz': 'UTC',
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1),
            'wage': 4400.0, **values,
        })
        employee.version_id.struct_id = self.structure
        return employee

    def _payslip(self, employee, date_from=date(2026, 6, 1), date_to=date(2026, 6, 30)):
        """ As the batch wizard makes them. """
        payslips = self.env['hr.payslip']
        values = payslips.onchange_employee_id(date_from, date_to, employee.id)['value']
        payslip = payslips.create({
            'employee_id': employee.id,
            'name': values.get('name'),
            'struct_id': values.get('struct_id'),
            'version_id': values.get('version_id'),
            'worked_days_line_ids': [Command.create(line) for line in values.get('worked_days_line_ids')],
            'input_line_ids': [Command.create(line) for line in values.get('input_line_ids')],
            'date_from': date_from,
            'date_to': date_to,
        })
        payslip.compute_sheet()
        return payslip

    @staticmethod
    def _totals(payslip):
        return {line.code: round(line.total, 2) for line in payslip.line_ids}

    def test_python_rule_zero_quantity_and_rate(self):
        """ A quantity or a rate of 0 returned by a python rule pays nothing, it is not the default. """
        category = self.env.ref('om_hr_payroll.ALW')
        self.structure.rule_ids |= self.env['hr.salary.rule'].create([{
            'name': 'No Hours', 'code': 'NOHOURS', 'sequence': 50, 'category_id': category.id,
            'amount_select': 'code', 'amount_python_compute': 'result = 100\nresult_qty = 0',
        }, {
            'name': 'No Rate', 'code': 'NORATE', 'sequence': 51, 'category_id': category.id,
            'amount_select': 'code', 'amount_python_compute': 'result = 100\nresult_rate = 0',
        }, {
            'name': 'Half', 'code': 'HALF', 'sequence': 52, 'category_id': category.id,
            'amount_select': 'code', 'amount_python_compute': 'result = 100\nresult_qty = 3\nresult_rate = 50',
        }])
        totals = self._totals(self._payslip(self._employee()))
        self.assertEqual(totals['NOHOURS'], 0.0)
        self.assertEqual(totals['NORATE'], 0.0)
        self.assertEqual(totals['HALF'], 150.0)

    def test_payslip_stored_without_credit_note(self):
        """ A payslip or a batch created without the credit note flag stores it False, not NULL: payslip.sum()
            subtracts the payslips whose flag is not False as refunds. """
        payslip = self._payslip(self._employee())
        run = self.env['hr.payslip.run'].create({
            'name': 'June', 'date_start': date(2026, 6, 1), 'date_end': date(2026, 6, 30),
        })
        self.env.flush_all()
        self.env.cr.execute("SELECT credit_note FROM hr_payslip WHERE id = %s", (payslip.id,))
        self.assertIs(self.env.cr.fetchone()[0], False)
        self.env.cr.execute("SELECT credit_note FROM hr_payslip_run WHERE id = %s", (run.id,))
        self.assertIs(self.env.cr.fetchone()[0], False)

    def test_child_rule_follows_its_parent_whatever_the_sequence(self):
        """ A child rule computed before its parent still applies only where the parent does. """
        category = self.env.ref('om_hr_payroll.ALW')
        parent = self.env['hr.salary.rule'].create({
            'name': 'Senior', 'code': 'SENIOR', 'sequence': 60, 'category_id': category.id,
            'condition_select': 'python', 'condition_python': 'result = contract.wage > 5000',
            'amount_select': 'fix', 'amount_fix': 100.0,
        })
        child = self.env['hr.salary.rule'].create({
            'name': 'Senior Bonus', 'code': 'SENIORBONUS', 'sequence': 50, 'category_id': category.id,
            'parent_rule_id': parent.id, 'amount_select': 'fix', 'amount_fix': 50.0,
        })
        self.structure.rule_ids |= parent | child
        totals = self._totals(self._payslip(self._employee()))
        self.assertNotIn('SENIOR', totals)
        self.assertNotIn('SENIORBONUS', totals)
        totals = self._totals(self._payslip(self._employee(wage=6000.0)))
        self.assertEqual(totals['SENIOR'], 100.0)
        self.assertEqual(totals['SENIORBONUS'], 50.0)

    def test_sum_of_the_confirmed_payslips(self):
        """ payslip.sum() adds the confirmed payslips, the ones stored without the credit note flag included, and
        takes the refunds off. """
        self.structure.rule_ids |= self.env['hr.salary.rule'].create({
            'name': 'Paid Before', 'code': 'PAIDBEFORE', 'sequence': 50,
            'category_id': self.env.ref('om_hr_payroll.ALW').id, 'amount_select': 'code',
            'amount_python_compute': "result = payslip.sum('BASIC', '2026-01-01', '2026-12-31')",
        })
        employee = self._employee()
        june = self._payslip(employee)
        june.write({'state': 'done'})
        self.env.flush_all()
        # as stored by an import or a script writing the table
        self.env.cr.execute("UPDATE hr_payslip SET credit_note = NULL WHERE id = %s", (june.id,))
        self.env.invalidate_all()

        july = self._payslip(employee, date(2026, 7, 1), date(2026, 7, 31))
        self.assertEqual(self._totals(july)['PAIDBEFORE'], 4400.0)

        refund = june.copy({'credit_note': True, 'name': 'Refund of June'})
        refund.compute_sheet()
        refund.write({'state': 'done'})
        july.compute_sheet()
        self.assertEqual(self._totals(july)['PAIDBEFORE'], 0.0)
