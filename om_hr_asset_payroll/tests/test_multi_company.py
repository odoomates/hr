from datetime import date

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAssetPayrollMultiCompany(TransactionCase):
    """ Two companies sharing the asset rule: each payslip deducts the asset charges of its own company. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env['res.company'].create({'name': 'Assets Company B'})
        if 'journal_id' in cls.env['hr.payslip']._fields:
            cls.env['account.journal'].create({
                'name': 'Salaries B', 'code': 'SALAB', 'type': 'general', 'company_id': cls.company_b.id})
        rules = cls.env.ref('om_hr_payroll.hr_rule_basic') | cls.env.ref('om_hr_asset_payroll.hr_rule_asset') \
            | cls.env.ref('om_hr_payroll.hr_rule_net')
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Shared Assets', 'code': 'ASSETMC', 'parent_id': False, 'company_id': False,
            'rule_ids': [Command.set(rules.ids)]})
        cls.employee_a = cls.new_employee(cls.env.company, 'Holder A')
        cls.employee_b = cls.new_employee(cls.company_b, 'Holder B')

    @classmethod
    def new_employee(cls, company, name):
        return cls.env['hr.employee'].with_company(company).create({
            'name': name, 'company_id': company.id, 'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1), 'wage': 3000.0, 'struct_id': cls.structure.id})

    def lose(self, employee, charge):
        """ :return: the assignment of an asset of the company of `employee`, lost with a charge """
        company = employee.company_id
        laptop = self.env['maintenance.equipment'].with_company(company).create({
            'name': 'Laptop of %s' % employee.name, 'company_id': company.id, 'employee_id': employee.id})
        self.env['hr.asset.wizard'].with_company(company).with_context(
            default_equipment_id=laptop.id, default_mode='lost').create(
            {'date': date(2026, 6, 10), 'charge_amount': charge}).action_confirm()
        return laptop.assignment_ids.filtered(lambda a: a.state == 'lost')

    def payslip(self, employee):
        with Form(self.env['hr.payslip'].with_company(employee.company_id)) as form:
            form.employee_id = employee
            form.date_from = date(2026, 6, 1)
            form.date_to = date(2026, 6, 30)
        payslip = form.record
        payslip.compute_sheet()
        return payslip

    def test_each_payslip_deducts_the_charges_of_its_company(self):
        lost_a, lost_b = self.lose(self.employee_a, 400.0), self.lose(self.employee_b, 250.0)
        self.assertEqual((lost_a.company_id, lost_b.company_id), (self.env.company, self.company_b))
        payslip_b = self.payslip(self.employee_b)
        self.assertEqual(sum(payslip_b.line_ids.filtered(lambda line: line.code == 'ASSET').mapped('total')), -250.0)
        self.assertEqual(lost_b.payslip_id, payslip_b)
        self.assertFalse(lost_a.payslip_id)

    def test_no_charge_on_a_payslip_of_another_company(self):
        lost_a = self.lose(self.employee_a, 400.0)
        payslip_b = self.payslip(self.employee_b)
        with self.assertRaises(UserError):
            lost_a.sudo().payslip_id = payslip_b
