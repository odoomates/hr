from datetime import date

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAssetPayroll(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        rules = cls.env.ref('om_hr_payroll.hr_rule_basic') | cls.env.ref('om_hr_asset_payroll.hr_rule_asset') \
            | cls.env.ref('om_hr_payroll.hr_rule_net')
        structure = cls.env['hr.payroll.structure'].create({
            'name': 'Asset Structure', 'code': 'ASSETTEST', 'parent_id': False, 'rule_ids': [Command.set(rules.ids)]})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Careless Holder', 'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1),
            'wage': 3000.0, 'struct_id': structure.id})
        cls.laptop = cls.env['maintenance.equipment'].create({'name': 'Payroll Laptop'})

    def lose(self, day, charge):
        self.laptop.write({'employee_id': self.employee.id, 'lost': False})
        self.env['hr.asset.wizard'].with_context(
            default_equipment_id=self.laptop.id, default_mode='lost').create(
            {'date': day, 'charge_amount': charge}).action_confirm()
        return self.laptop.assignment_ids.filtered(lambda a: a.state == 'lost' and a.date_to == day)

    def payslip(self, month):
        with Form(self.env['hr.payslip']) as form:
            form.employee_id = self.employee
            form.date_from = date(2026, month, 1)
            form.date_to = date(2026, month, 28)
        payslip = form.record
        payslip.compute_sheet()
        return payslip

    @staticmethod
    def total(payslip, code):
        return sum(payslip.line_ids.filtered(lambda line: line.code == code).mapped('total'))

    def test_charge_deducted_once(self):
        lost = self.lose(date(2026, 6, 10), 400.0)
        june = self.payslip(6)
        self.assertEqual(self.total(june, 'ASSET'), -400.0)
        self.assertEqual(self.total(june, 'NET'), 2600.0)
        self.assertEqual(lost.payslip_id, june)
        june.write({'state': 'done'})
        self.assertEqual(self.total(self.payslip(7), 'ASSET'), 0.0, 'not twice')

    def test_cancelled_payslip_releases_the_charge(self):
        lost = self.lose(date(2026, 6, 10), 400.0)
        june = self.payslip(6)
        june.action_payslip_cancel()
        self.assertFalse(lost.payslip_id)
        self.assertEqual(self.total(self.payslip(6), 'ASSET'), -400.0)

    def test_later_charge_waits_for_its_month(self):
        self.lose(date(2026, 7, 5), 250.0)
        self.assertEqual(self.total(self.payslip(6), 'ASSET'), 0.0)
        self.assertEqual(self.total(self.payslip(7), 'ASSET'), -250.0)
