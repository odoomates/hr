from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalMultiCompanyCase


@tagged('post_install', '-at_install')
class TestPortalLoanMultiCompany(HrPortalMultiCompanyCase):

    def test_types_and_loans_of_the_company(self):
        Type = self.env['hr.loan.type']
        type_a = Type.create({'name': 'Loan of Company A', 'company_id': self.company_a.id})
        type_b = Type.create({'name': 'Loan of Company B', 'company_id': self.company_b.id})
        loan_a = self.env['hr.loan'].create({
            'employee_id': self.employee.id, 'type_id': type_a.id, 'amount': 500.0, 'installment_count': 1})
        self.login_employee_b()
        page = self.get('/my/hr/loans').text
        self.assertIn(type_b.name, page)
        self.assertNotIn(type_a.name, page)
        self.assertEqual(self.get('/my/hr/loans/%s' % loan_a.id).status_code, 404)
