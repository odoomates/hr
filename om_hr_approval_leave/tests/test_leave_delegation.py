from datetime import date

from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestLeaveDelegation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_user = new_test_user(cls.env, 'om_leave_approver',
                                          groups='base.group_user,hr_holidays.group_hr_holidays_employee')
        cls.manager_user = new_test_user(cls.env, 'om_leave_manager', groups='base.group_user')
        cls.substitute = new_test_user(cls.env, 'om_leave_substitute', groups='base.group_user')
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': 'Leave Manager', 'user_id': cls.manager_user.id})
        cls.approver = Employee.create({'name': 'Leave Approver', 'user_id': cls.approver_user.id,
                                        'parent_id': cls.manager.id})
        cls.leave_type = cls.env['hr.work.entry.type'].create({
            'name': 'Delegation Leave', 'code': 'DELEGLEAVE', 'count_as': 'absence', 'requires_allocation': False,
            'time_off_selectable': True, 'leave_validation_type': 'hr'})

    def leave(self):
        # asked by the employee: it waits for its approval
        return self.env['hr.leave'].with_user(self.approver_user).create({
            'employee_id': self.approver.id, 'work_entry_type_id': self.leave_type.id,
            'request_date_from': date(2026, 12, 7), 'request_date_to': date(2026, 12, 9)})

    def delegation(self, leave):
        return self.env['approval.delegation'].with_context(active_test=False).search([('leave_id', '=', leave.id)])

    def test_substitute_during_the_time_off(self):
        self.approver_user.approval_substitute_id = self.substitute
        leave = self.leave()
        self.assertFalse(self.delegation(leave), 'not before the time off is approved')
        leave.sudo().action_approve()
        delegation = self.delegation(leave)
        self.assertEqual((delegation.user_id, delegation.delegate_id), (self.approver_user, self.substitute))
        self.assertEqual((delegation.date_from, delegation.date_to), (date(2026, 12, 7), date(2026, 12, 9)))
        leave.sudo().action_refuse()
        self.assertFalse(self.delegation(leave), 'refused: nobody stands in')

    def test_manager_without_substitute(self):
        leave = self.leave()
        leave.sudo().action_approve()
        self.assertEqual(self.delegation(leave).delegate_id, self.manager_user)
