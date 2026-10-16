from datetime import date

from odoo.tests import tagged

from odoo.addons.om_hr_portal.tests.common import HrPortalCase

@tagged('post_install', '-at_install')
class TestPortalLoan(HrPortalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loan_type = cls.env['hr.loan.type'].create({'name': 'Portal Loan', 'single_running': False})
        cls.colleague_loan = cls.env['hr.loan'].create({
            'employee_id': cls.colleague.id, 'type_id': cls.loan_type.id, 'amount': 500.0, 'installment_count': 1})

    def test_request_and_follow(self):
        self.login_employee()
        response = self.url_open('/my/hr/loans/new', data={
            'csrf_token': self.csrf_token(), 'type_id': self.loan_type.id, 'amount': '900',
            'installment_count': '3', 'date_start': '2026-12', 'reason': 'Car repair'}, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        loan = self.env['hr.loan'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual((loan.state, loan.amount, len(loan.line_ids)), ('to_approve', 900.0, 3))
        self.assertEqual(loan.date_start, date(2026, 12, 1))
        self.assertEqual(loan.approver_user_ids, self.manager_user, 'waiting for the manager')
        page = self.get('/my/hr/loans/%s' % loan.id)
        self.assertIn('December 2026', page.text)
        self.assertNotIn(self.colleague_loan.name, self.get('/my/hr/loans').text)

    def test_no_one_else_s_loan(self):
        self.login_employee()
        self.assertEqual(self.get('/my/hr/loans/%s' % self.colleague_loan.id).status_code, 404)

    def test_no_loan_type_of_another_company(self):
        other_company = self.env['res.company'].create({'name': 'Other Loan Company'})
        foreign_type = self.env['hr.loan.type'].create({'name': 'Foreign Loan', 'company_id': other_company.id})
        self.login_employee()
        response = self.url_open('/my/hr/loans/new', data={
            'csrf_token': self.csrf_token(), 'type_id': foreign_type.id, 'amount': '500', 'installment_count': '1'})
        self.assertEqual(response.status_code, 200, 'the form again, with the error')
        self.assertIn('Choose a type of loan.', response.text)
        self.assertFalse(self.env['hr.loan'].search([('employee_id', '=', self.employee.id)]))
