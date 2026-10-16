from datetime import date

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestLoan(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_user = new_test_user(cls.env, 'om_loan_employee', groups='base.group_user')
        cls.manager_user = new_test_user(cls.env, 'om_loan_manager', groups='base.group_user')
        cls.hr_user = new_test_user(cls.env, 'om_loan_hr', groups='base.group_user,hr.group_hr_user')
        cls.hr_admin = new_test_user(cls.env, 'om_loan_hr_admin', groups='base.group_user,hr.group_hr_manager')
        cls.env.ref('om_hr_loan.flow_om_hr_loan_hr').group_id = cls.env['res.groups'].create({
            'name': 'Loan Approvers', 'user_ids': [Command.link(cls.hr_admin.id)]})
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': 'Loan Manager', 'user_id': cls.manager_user.id})
        cls.employee = Employee.create({
            'name': 'Loan Employee', 'user_id': cls.employee_user.id, 'parent_id': cls.manager.id,
            'date_version': date(2024, 1, 1), 'contract_date_start': date(2024, 1, 1), 'wage': 3000.0})
        cls.loan_type = cls.env['hr.loan.type'].create({'name': 'Test Loan', 'max_installments': 12})

    def new_loan(self, amount=1000.0, count=3, **values):
        return self.env['hr.loan'].with_user(self.employee_user).create({
            'employee_id': self.employee.id, 'type_id': self.loan_type.id, 'amount': amount,
            'installment_count': count, 'date': date(2026, 7, 10), 'date_start': date(2026, 8, 15), **values})

    def approve(self, loan):
        loan.with_user(self.employee_user).action_submit()
        loan.with_user(self.manager_user).action_approval_approve()
        loan.with_user(self.hr_admin).action_approval_approve()

    def test_installments(self):
        loan = self.new_loan()
        loan.action_compute_installments()
        self.assertEqual(loan.line_ids.mapped('amount'), [333.33, 333.33, 333.34])
        self.assertEqual(loan.line_ids.mapped('date'), [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)])
        loan.with_user(self.employee_user).amount = 1200
        self.assertEqual(loan.line_ids.mapped('amount'), [400, 400, 400], 'the schedule follows the amount')

    def test_approve_pay_out_and_repay(self):
        loan = self.new_loan()
        loan.with_user(self.employee_user).action_submit()
        self.assertEqual((loan.state, loan.approval_step), ('to_approve', 'Manager'))
        self.assertEqual(len(loan.line_ids), 3, 'submitting computes the installments')
        with self.assertRaises(UserError):
            loan.with_user(self.employee_user).action_approval_approve()
        loan.with_user(self.manager_user).action_approval_approve()
        loan.with_user(self.hr_admin).action_approval_approve()
        self.assertEqual(loan.state, 'approved')

        with self.assertRaises(UserError):
            loan.with_user(self.employee_user).action_disburse()
        loan.with_user(self.hr_user).action_disburse()
        self.assertEqual(loan.state, 'running')
        self.assertEqual(loan.amount_residual, 1000)

        loan.line_ids[0].with_user(self.hr_user).action_mark_paid()
        self.assertEqual((loan.amount_paid, loan.amount_residual), (333.33, 666.67))
        loan.with_user(self.hr_user).action_settle()
        self.assertEqual(loan.state, 'paid')
        self.assertEqual(loan.amount_residual, 0)

    def test_refuse(self):
        loan = self.new_loan()
        loan.with_user(self.employee_user).action_submit()
        loan.with_user(self.manager_user).action_approval_refuse('Not now')
        self.assertEqual(loan.state, 'refused')
        loan.with_user(self.employee_user).action_approval_reset()
        self.assertEqual(loan.state, 'draft')

    def test_postpone(self):
        loan = self.new_loan()
        self.approve(loan)
        loan.with_user(self.hr_user).action_disburse()
        loan.line_ids[1].with_user(self.hr_user).action_postpone()
        self.assertEqual(loan.line_ids.sorted('sequence').mapped('date'),
                         [date(2026, 8, 1), date(2026, 10, 1), date(2026, 11, 1)])

    def test_limits(self):
        self.loan_type.max_amount = 500
        with self.assertRaises(UserError):
            self.new_loan().action_submit()
        self.loan_type.write({'max_amount': 0, 'max_installments': 2})
        with self.assertRaises(UserError):
            self.new_loan().action_submit()
        self.loan_type.write({'max_installments': 0, 'max_wage_percent': 10})
        with self.assertRaises(UserError, msg='300 is 10% of the wage, 333.33 is more'):
            self.new_loan().action_submit()
        self.loan_type.write({'max_wage_percent': 0, 'min_service_months': 36})
        with self.assertRaises(UserError):
            self.new_loan().action_submit()

    def test_one_at_a_time(self):
        self.new_loan().with_user(self.employee_user).action_submit()
        with self.assertRaises(UserError):
            self.new_loan().with_user(self.employee_user).action_submit()
        self.loan_type.single_running = False
        self.new_loan().with_user(self.employee_user).action_submit()

    def test_advance(self):
        self.loan_type.is_advance = True
        with Form(self.env['hr.loan'].with_user(self.employee_user)) as form:
            form.type_id = self.loan_type
            form.amount = 900
        self.assertEqual(form.record.installment_count, 1)
        form.record.action_compute_installments()
        self.assertEqual(form.record.line_ids.mapped('amount'), [900])

    def test_access(self):
        loan = self.new_loan()
        loan.with_user(self.employee_user).action_submit()
        with self.assertRaises(AccessError):
            loan.with_user(self.employee_user).reason = 'Changed once submitted'
        other = new_test_user(self.env, 'om_loan_other', groups='base.group_user')
        self.assertFalse(self.env['hr.loan'].with_user(other).search([('id', '=', loan.id)]))
        self.assertTrue(self.env['hr.loan'].with_user(self.manager_user).search([('id', '=', loan.id)]))
