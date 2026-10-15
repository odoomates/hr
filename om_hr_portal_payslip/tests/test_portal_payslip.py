from datetime import date

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.om_hr_portal.tests.common import OmHrPortalCase


@tagged('post_install', '-at_install')
class TestPortalPayslip(OmHrPortalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        rules = cls.env.ref('om_hr_payroll.hr_rule_basic') | cls.env.ref('om_hr_payroll.hr_rule_net')
        structure = cls.env['hr.payroll.structure'].create({
            'name': 'Portal Structure', 'code': 'PORTALTEST', 'parent_id': False,
            'rule_ids': [Command.set(rules.ids)]})
        (cls.employee | cls.colleague).write({'struct_id': structure.id})
        cls.own = cls._payslip(cls.employee, 'done')
        cls.draft = cls._payslip(cls.employee, 'draft')
        cls.others = cls._payslip(cls.colleague, 'done')

    @classmethod
    def _payslip(cls, employee, state):
        with Form(cls.env['hr.payslip']) as form:
            form.employee_id = employee
            form.date_from = date(2026, 6, 1)
            form.date_to = date(2026, 6, 30)
        payslip = form.record
        payslip.compute_sheet()
        payslip.write({'state': state, 'number': 'SLIP/PORTAL/%s' % payslip.id})
        return payslip

    def test_list_detail_and_pdf(self):
        self.login_employee()
        page = self.get('/my/hr/payslips')
        self.assertIn(self.own.name, page.text)
        self.assertIn('/my/hr/payslips/%s' % self.own.id, page.text)
        self.assertNotIn('/my/hr/payslips/%s' % self.draft.id, page.text)
        detail = self.get('/my/hr/payslips/%s' % self.own.id)
        self.assertEqual(detail.status_code, 200)
        self.assertIn('3,000.00', detail.text)
        pdf = self.get('/my/payslip/%s/pdf' % self.own.id)
        self.assertEqual((pdf.status_code, pdf.headers['Content-Type']), (200, 'application/pdf'))
        self.assertIn('Payslips', self.get('/my/hr').text, 'the card on My HR')

    def test_no_one_else_s_payslip(self):
        self.login_employee()
        self.assertEqual(self.get('/my/hr/payslips/%s' % self.others.id).status_code, 404)
        self.assertEqual(self.get('/my/hr/payslips/%s' % self.draft.id).status_code, 404)
        self.assertEqual(self.get('/my/payslip/%s/pdf' % self.others.id).status_code, 404)
