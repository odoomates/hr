from datetime import date

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import Form, HttpCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestPayslipSelf(HttpCase):
    """ An employee with a light user of Odoo 20 reads their own confirmed payslips, and nothing else. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, 'om_payslip_self', groups='base.group_user')
        cls.other_user = new_test_user(cls.env, 'om_payslip_other', groups='base.group_user')
        rules = cls.env.ref('om_hr_payroll.hr_rule_basic') | cls.env.ref('om_hr_payroll.hr_rule_net')
        structure = cls.env['hr.payroll.structure'].create({
            'name': 'Self Structure', 'code': 'SELFTEST', 'parent_id': False, 'rule_ids': [Command.set(rules.ids)]})
        Employee = cls.env['hr.employee']
        values = {'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1), 'wage': 3000.0,
                  'struct_id': structure.id}
        cls.employee = Employee.create({'name': 'Self Employee', 'user_id': cls.user.id, **values})
        cls.other = Employee.create({'name': 'Other Employee', 'user_id': cls.other_user.id, **values})
        cls.own = cls._payslip(cls.employee, 6, 'done')
        cls.own_draft = cls._payslip(cls.employee, 7, 'draft')
        cls.others = cls._payslip(cls.other, 6, 'done')

    @classmethod
    def _payslip(cls, employee, month, state):
        with Form(cls.env['hr.payslip']) as form:
            form.employee_id = employee
            form.date_from = date(2026, month, 1)
            form.date_to = date(2026, month, 28)
        payslip = form.record
        payslip.compute_sheet()
        payslip.write({'state': state, 'number': 'SLIP/SELF/%s' % payslip.id})
        return payslip

    def test_light_user(self):
        self.assertEqual(self.user.role, 'light_user', 'an Odoo 20 light user')

    def test_reads_only_own_confirmed_payslips(self):
        Payslip = self.env['hr.payslip'].with_user(self.user)
        self.assertEqual(Payslip.search([]), self.own)
        self.assertEqual(self.own.with_user(self.user).line_ids.mapped('code'), ['BASIC', 'NET'])
        for payslip in (self.own_draft, self.others):
            with self.assertRaises(AccessError):
                payslip.with_user(self.user).read(['name'])
        with self.assertRaises(AccessError):
            self.own.with_user(self.user).write({'note': 'mine'})

    def test_my_hr_menu(self):
        visible = self.env['ir.ui.menu'].with_user(self.user)._visible_menu_ids()
        self.assertIn(self.env.ref('om_hr_payroll.menu_my_hr_payslips').id, visible)
        self.assertIn(self.env.ref('om_hr_base.menu_my_hr').id, visible)

    def test_pdf_only_for_its_employee(self):
        self.authenticate('om_payslip_self', 'om_payslip_self')
        response = self.url_open('/my/payslip/%s/pdf' % self.own.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/pdf')
        self.assertEqual(self.url_open('/my/payslip/%s/pdf' % self.others.id).status_code, 404)
        self.assertEqual(self.url_open('/my/payslip/%s/pdf' % self.own_draft.id).status_code, 404)
