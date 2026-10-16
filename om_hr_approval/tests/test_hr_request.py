from datetime import timedelta

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestHrRequest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_user = new_test_user(cls.env, 'om_hr_employee', groups='base.group_user')
        cls.manager_user = new_test_user(cls.env, 'om_hr_manager', groups='base.group_user')
        cls.colleague_user = new_test_user(cls.env, 'om_hr_colleague', groups='base.group_user')
        cls.hr_user = new_test_user(cls.env, 'om_hr_officer', groups='base.group_user,hr.group_hr_user')
        cls.hr_admin = new_test_user(cls.env, 'om_hr_admin', groups='base.group_user,hr.group_hr_manager')
        # only our officer approves the HR step, whatever users the database already has
        cls.hr_group = cls.env['res.groups'].create({'name': 'HR Request Approvers', 'user_ids': [
            Command.link(cls.hr_user.id)]})
        cls.env.ref('om_hr_approval.flow_om_hr_request_hr').group_id = cls.hr_group
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': 'Manager', 'user_id': cls.manager_user.id})
        cls.employee = Employee.create({'name': 'Employee', 'user_id': cls.employee_user.id,
                                        'parent_id': cls.manager.id})
        Employee.create({'name': 'Colleague', 'user_id': cls.colleague_user.id, 'parent_id': cls.manager.id})
        cls.category = cls.env.ref('om_hr_approval.request_category_document')

    def new_request(self, user=None, employee=None):
        return self.env['hr.request'].with_user(user or self.employee_user).create({
            'employee_id': (employee or self.employee).id, 'category_id': self.category.id,
            'description': 'A salary certificate for the bank'})

    def test_manager_then_hr(self):
        request = self.new_request()
        self.assertTrue(request.name.startswith('REQ/'))
        request.action_approval_submit()
        self.assertEqual(request.approval_state, 'to_approve')
        self.assertEqual(request.approval_step, 'Manager')
        self.assertEqual(request.approver_user_ids, self.manager_user)

        manager_view = request.with_user(self.manager_user)
        self.assertTrue(manager_view.can_approve)
        self.assertFalse(request.with_user(self.colleague_user).search([('id', '=', request.id)]),
                         'a colleague does not see the request')
        manager_view.action_approval_approve()
        self.assertEqual((request.approval_state, request.approval_step), ('to_approve', 'HR'))
        self.assertEqual(request.approver_user_ids, self.hr_user)

        request.with_user(self.hr_user).action_approval_approve()
        self.assertEqual(request.approval_state, 'approved')
        self.assertEqual(request.approval_line_ids.mapped('state'), ['approved', 'approved'])

    def test_refuse_and_resubmit(self):
        request = self.new_request()
        request.action_approval_submit()
        wizard_action = request.with_user(self.manager_user).action_approval_open_refuse()
        self.env['approval.refuse'].with_user(self.manager_user).create({
            'request_id': wizard_action['context']['default_request_id'], 'reason': 'Ask the bank first'},
        ).action_refuse()
        self.assertEqual(request.approval_state, 'refused')
        request.action_approval_reset()
        self.assertEqual(request.approval_state, 'draft')
        request.action_approval_submit()
        self.assertEqual(request.approval_state, 'to_approve')
        self.assertEqual(len(request.approval_request_ids), 2, 'the refused round stays in the history')

    def test_without_manager(self):
        """ Nobody manages the employee: the HR administrators approve the manager step. """
        self.employee.parent_id = False
        request = self.new_request()
        request.action_approval_submit()
        self.assertIn(self.hr_admin, request.approver_user_ids)
        self.assertNotIn(self.employee_user, request.approver_user_ids)

    def test_hr_asks_for_the_manager(self):
        """ The employee a request is for never approves it, even when HR asks on his behalf. """
        request = self.new_request(user=self.hr_user, employee=self.manager)
        request.with_user(self.hr_user).action_approval_submit()
        self.assertNotIn(self.manager_user, request.approver_user_ids)

    def test_only_draft_changes(self):
        request = self.new_request()
        request.action_approval_submit()
        with self.assertRaises(AccessError):
            request.with_user(self.employee_user).description = 'Changed'
        with self.assertRaises(UserError):
            request.with_user(self.colleague_user).action_approval_approve()
        with self.assertRaises(UserError):
            request.sudo().unlink()

    def test_manager_approver_on_any_button(self):
        """ The manager of the requester approves a button of another app. """
        button = self.env['approval.button'].create({
            'model_id': self.env['ir.model']._get_id('res.partner'), 'method': 'action_archive', 'name': 'Archive'})
        self.env['approval.rule'].create({
            'name': 'Archive', 'model_id': button.model_id.id, 'button_id': button.id,
            'step_ids': [Command.create({'name': 'Manager', 'approver_type': 'manager'})]})
        self.employee_user.group_ids = [Command.link(self.env.ref('base.group_partner_manager').id)]
        partner = self.env['res.partner'].create({'name': 'Customer'})
        self.env['approval.request'].with_user(self.employee_user)._gate_button(
            'res.partner', 'action_archive', partner.ids)
        request = self.env['approval.request'].search([('res_model', '=', 'res.partner'),
                                                         ('res_id', '=', partner.id)])
        self.assertEqual(request.approver_user_ids, self.manager_user)

    def test_escalate_to_the_manager_of_the_approver(self):
        boss_user = new_test_user(self.env, 'om_hr_boss', groups='base.group_user')
        self.manager.parent_id = self.env['hr.employee'].create({'name': 'Boss', 'user_id': boss_user.id})
        step = self.env.ref('om_hr_approval.flow_om_hr_request_manager')
        self.assertEqual(self.env['approval.step'].new({}).escalate_type, 'manager', 'the default with HR')
        step.write({'escalate_days': 2, 'escalate_type': 'manager'})
        request = self.new_request()
        request.action_approval_submit()
        line = request.approval_line_ids.filtered(lambda line: line.state == 'pending')
        self.assertEqual(line.approver_user_ids, self.manager_user)
        with freeze_time(fields.Datetime.now() + timedelta(days=2, hours=1)):
            self.env['approval.line']._cron_follow_up()
        self.assertEqual(line.approver_user_ids, self.manager_user | boss_user)
