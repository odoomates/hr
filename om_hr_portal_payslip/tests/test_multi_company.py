from datetime import date

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalMultiCompanyCase


@tagged('post_install', '-at_install')
class TestPortalPayslipMultiCompany(HrPortalMultiCompanyCase):

    def test_payslip_of_the_other_company(self):
        rules = self.env.ref('om_hr_payroll.hr_rule_basic') | self.env.ref('om_hr_payroll.hr_rule_net')
        structure = self.env['hr.payroll.structure'].create({
            'name': 'Portal MC Structure', 'code': 'PORTALMC', 'parent_id': False, 'company_id': False,
            'rule_ids': [Command.set(rules.ids)]})
        self.employee.struct_id = structure
        with Form(self.env['hr.payslip']) as form:
            form.employee_id = self.employee
            form.date_from = date(2026, 6, 1)
            form.date_to = date(2026, 6, 30)
        payslip = form.record
        payslip.compute_sheet()
        payslip.write({'state': 'done', 'number': 'SLIP/MC/%s' % payslip.id})
        self.login_employee_b()
        self.assertNotIn(payslip.number, self.get('/my/hr/payslips').text)
        self.assertEqual(self.get('/my/hr/payslips/%s' % payslip.id).status_code, 404)
        self.assertEqual(self.get('/my/payslip/%s/pdf' % payslip.id).status_code, 404)
