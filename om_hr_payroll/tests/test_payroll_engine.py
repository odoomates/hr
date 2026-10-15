from datetime import date

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPayrollEngine(TransactionCase):
    """ Pay for part of a period, rounding of the rules, and retro pay. June 2026 has 22 working days. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env['resource.calendar'].create({'name': 'Engine 40h'})
        cls.rules = (
            cls.env.ref('om_hr_payroll.hr_rule_basic')
            | cls.env.ref('om_hr_payroll.hr_rule_partial_period')
            | cls.env.ref('om_hr_payroll.hr_rule_retro')
            | cls.env.ref('om_hr_payroll.hr_rule_taxable')
            | cls.env.ref('om_hr_payroll.hr_rule_net')
        )
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Engine Structure', 'code': 'ENGINETEST', 'parent_id': False,
            'rule_ids': [Command.set(cls.rules.ids)],
        })

    def _employee(self, **values):
        return self.env['hr.employee'].create({
            'name': 'Engine Employee', 'resource_calendar_id': self.calendar.id, 'tz': 'UTC',
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1),
            'wage': 4400.0, 'struct_id': self.structure.id, **values,
        })

    def _payslip(self, employee, date_from=date(2026, 6, 1), date_to=date(2026, 6, 30)):
        """ Through the form, as the user and the batch wizard do: that is what fills the worked days. """
        with Form(self.env['hr.payslip']) as payslip_form:
            payslip_form.employee_id = employee
            payslip_form.date_from = date_from
            payslip_form.date_to = date_to
        payslip = payslip_form.record
        payslip.compute_sheet()
        return payslip

    @staticmethod
    def _totals(payslip):
        return {line.code: round(line.total, 2) for line in payslip.line_ids}

    def test_whole_period_is_not_prorated(self):
        totals = self._totals(self._payslip(self._employee()))
        self.assertNotIn('PARTIAL', totals)
        self.assertEqual(totals['NET'], 4400.0)

    def test_joiner_mid_month(self):
        """ Joins on Monday 15 June: 12 working days out of 22. """
        employee = self._employee(date_version=date(2026, 6, 15), contract_date_start=date(2026, 6, 15))
        totals = self._totals(self._payslip(employee))
        self.assertEqual(totals['PARTIAL'], -2000.0)
        self.assertEqual(totals['NET'], 2400.0)

    def test_leaver_on_the_19th(self):
        """ Leaves on Friday 19 June: 15 working days out of 22. """
        employee = self._employee(contract_date_end=date(2026, 6, 19))
        totals = self._totals(self._payslip(employee))
        self.assertEqual(totals['PARTIAL'], -1400.0)
        self.assertEqual(totals['NET'], 3000.0)

    def test_short_payslip_under_contract_is_not_prorated(self):
        """ Only the contract dates count: a payslip ending before the end of the month pays the whole wage. """
        totals = self._totals(self._payslip(self._employee(), date_to=date(2026, 6, 28)))
        self.assertNotIn('PARTIAL', totals)
        self.assertEqual(totals['NET'], 4400.0)

    def test_rounding(self):
        third = self.env['hr.salary.rule'].create({
            'name': 'Third', 'code': 'THIRD', 'sequence': 50, 'category_id': self.env.ref('om_hr_payroll.ALW').id,
            'amount_select': 'code', 'amount_python_compute': 'result = contract.wage / 3',
            'rounding_precision': 5.0,
        })
        self.structure.rule_ids |= third
        employee = self._employee()
        for method, expected in (('none', 1466.67), ('half', 1465.0), ('up', 1470.0), ('down', 1465.0)):
            third.rounding_method = method
            payslip = self._payslip(employee)
            totals = self._totals(payslip)
            self.assertEqual(totals['THIRD'], expected, method)
            self.assertEqual(totals['NET'], round(4400.0 + expected, 2), '%s: the net adds the rounded line' % method)
            payslip.unlink()
        third.rounding_method = 'up'
        self.assertEqual(third._round(-1466.67), -1470.0, 'a deduction rounded up is a larger deduction')

    def test_retro_pay(self):
        """ A raise from 3,000 to 3,300 dated back to 1 August is paid on the September payslip. """
        employee = self._employee(wage=3000.0)
        august = self._payslip(employee, date(2026, 8, 1), date(2026, 8, 31))
        self.assertEqual(self._totals(august)['NET'], 3000.0)
        # confirmed as is: no journal entry when payroll accounting is installed
        august.write({'state': 'done', 'number': 'SLIP/AUG'})

        employee.create_version({'date_version': date(2026, 8, 1), 'wage': 3300.0})
        september = self._payslip(employee, date(2026, 9, 1), date(2026, 9, 30))
        retro = self.env['hr.payslip.retro'].create({'payslip_id': september.id, 'date_from': date(2026, 8, 1)})
        retro.action_apply()

        retro_input = september.input_line_ids.filtered(lambda line: line.code == 'RETRO')
        self.assertEqual(retro_input.amount, 300.0)
        self.assertIn('August 2026', retro_input.name)
        totals = self._totals(september)
        self.assertEqual(totals['RETRO'], 300.0)
        self.assertEqual(totals['NET'], 3600.0)
        # the August payslip is left as it was
        self.assertEqual(self._totals(august)['NET'], 3000.0)
        self.assertEqual(august.number, 'SLIP/AUG')
        self.assertEqual(self.env['hr.payslip'].search_count([('number', '=', 'RETRO')]), 0)

        # applied again, the input is replaced, not added
        retro.action_apply()
        self.assertEqual(len(september.input_line_ids.filtered(lambda line: line.code == 'RETRO')), 1)
