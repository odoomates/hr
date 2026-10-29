# -*- coding: utf-8 -*-

from odoo.fields import Date
from odoo.tests.common import TransactionCase


class TestPayslipBase(TransactionCase):
    """ An employee under contract for a structure of allowances and deductions, built by the test itself: the
    module ships no demo data. """

    def setUp(self):
        super(TestPayslipBase, self).setUp()
        self.house_rent_register = self.env['hr.contribution.register'].create({'name': 'House Rent'})
        allowance = self.env.ref('om_hr_payroll.ALW')
        deduction = self.env.ref('om_hr_payroll.DED')
        self.rules = self.env['hr.salary.rule'].create([{
            'name': 'House Rent Allowance', 'code': 'HRA', 'sequence': 5, 'category_id': allowance.id,
            'register_id': self.house_rent_register.id,
            'amount_select': 'percentage', 'amount_percentage': 40.0, 'amount_percentage_base': 'contract.wage',
        }, {
            'name': 'Conveyance Allowance', 'code': 'CA', 'sequence': 10, 'category_id': allowance.id,
            'amount_select': 'fix', 'amount_fix': 800.0,
        }, {
            'name': 'Sales Commission', 'code': 'SALECOMM', 'sequence': 15, 'category_id': allowance.id,
            'amount_select': 'code', 'amount_python_compute': 'result = inputs.SALEURO and inputs.SALEURO.amount',
            'input_ids': [(0, 0, {'name': 'Sales in Euro', 'code': 'SALEURO'})],
        }, {
            'name': 'Professional Tax', 'code': 'PT', 'sequence': 150, 'category_id': deduction.id,
            'amount_select': 'fix', 'amount_fix': -200.0,
        }, {
            'name': 'Provident Fund', 'code': 'PF', 'sequence': 160, 'category_id': deduction.id,
            'amount_select': 'percentage', 'amount_percentage': -12.5, 'amount_percentage_base': 'contract.wage',
        }])
        self.developer_pay_structure = self.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for Software Developer',
            'code': 'SD',
            'parent_id': self.ref('om_hr_payroll.structure_base'),
            'rule_ids': [(6, 0, self.rules.ids)],
        })
        self.richard_emp = self.env['hr.employee'].create({'name': 'Richard'})
        self.richard_contract = self.env['hr.contract'].create({
            'name': 'Contract for Richard',
            'date_start': Date.to_date('2011-01-01'),
            'wage': 5000.0,
            'employee_id': self.richard_emp.id,
            'struct_id': self.developer_pay_structure.id,
            'state': 'open',
        })

    def _new_payslip(self, date_from='2011-09-01', date_to='2011-09-30', **values):
        """ The payslip as the form fills it in: its contract, structure, worked days and inputs. """
        payslip_model = self.env['hr.payslip']
        onchange = payslip_model.onchange_employee_id(date_from, date_to, self.richard_emp.id)['value']
        return payslip_model.create(dict({
            'name': onchange['name'],
            'employee_id': self.richard_emp.id,
            'contract_id': onchange['contract_id'],
            'struct_id': onchange['struct_id'],
            'date_from': date_from,
            'date_to': date_to,
            'worked_days_line_ids': [(0, 0, line) for line in onchange['worked_days_line_ids']],
            'input_line_ids': [(0, 0, line) for line in onchange['input_line_ids']],
        }, **values))

    @staticmethod
    def _totals(payslip):
        return {line.code: line.total for line in payslip.line_ids}
