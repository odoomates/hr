from datetime import date, timedelta

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestExit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_user = new_test_user(cls.env, 'om_exit_employee', groups='base.group_user')
        cls.manager_user = new_test_user(cls.env, 'om_exit_manager', groups='base.group_user')
        cls.hr_user = new_test_user(cls.env, 'om_exit_hr', groups='base.group_user,hr.group_hr_user')
        cls.hr_admin = new_test_user(cls.env, 'om_exit_hr_admin', groups='base.group_user,hr.group_hr_manager')
        cls.it_user = new_test_user(cls.env, 'om_exit_it', groups='base.group_user')
        cls.env.ref('om_hr_exit.flow_om_hr_exit_hr').group_id = cls.env['res.groups'].create({
            'name': 'Exit Approvers', 'user_ids': [Command.link(cls.hr_admin.id)]})
        # a checklist of our own: the manager and IT
        cls.env['hr.exit.checklist'].search([]).active = False
        cls.env['hr.exit.checklist'].create([
            {'name': 'Handover', 'responsible_type': 'manager'},
            {'name': 'Laptop', 'responsible_type': 'user', 'user_ids': [Command.link(cls.it_user.id)]},
            {'name': 'Retirement gift', 'responsible_type': 'user', 'user_ids': [Command.link(cls.it_user.id)],
             'departure_reason_ids': [Command.link(cls.env.ref('hr.departure_retired').id)]},
        ])
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': 'Exit Manager', 'user_id': cls.manager_user.id})
        cls.employee = Employee.create({
            'name': 'Leaving Employee', 'user_id': cls.employee_user.id, 'parent_id': cls.manager.id,
            'date_version': date(2024, 1, 1), 'contract_date_start': date(2024, 1, 1), 'wage': 3000.0})

    def resign(self, date_notice=None, notice_days=None):
        values = {'employee_id': self.employee.id, 'note': 'A new job abroad'}
        if date_notice:
            values['date_notice'] = date_notice
        if notice_days is not None:
            values['notice_days'] = notice_days
        exit_ = self.env['hr.exit'].with_user(self.employee_user).create(values)
        return exit_

    def approve(self, exit_):
        exit_.with_user(self.employee_user).action_submit()
        exit_.with_user(self.manager_user).action_approval_approve()
        exit_.with_user(self.hr_admin).action_approval_approve()

    def test_notice_period(self):
        self.env.company.hr_exit_notice_days = 60
        exit_ = self.resign(date_notice=date(2026, 3, 1))
        self.assertEqual(exit_.departure_reason_id, self.env.ref('hr.departure_resigned'))
        self.assertEqual(exit_.notice_days, 60)
        self.assertEqual(exit_.last_working_day, date(2026, 4, 30))

    def test_resignation_to_departure(self):
        today = fields.Date.context_today(self.env['hr.exit'])
        exit_ = self.resign(date_notice=today - timedelta(days=40), notice_days=30)
        self.approve(exit_)
        self.assertEqual(exit_.state, 'approved')
        self.assertEqual(exit_.clearance_ids.mapped('name'), ['Handover', 'Laptop'],
                         'the retirement item is only for the retirements')
        handover, laptop = exit_.clearance_ids
        self.assertEqual(handover.responsible_user_ids, self.manager_user)
        self.assertEqual(len(exit_.activity_ids), 2)
        self.assertEqual(exit_.clearance_progress, 0)

        with self.assertRaises(UserError):
            exit_.with_user(self.hr_user).action_done()
        with self.assertRaises(UserError):
            laptop.with_user(self.manager_user).action_clear()
        handover.with_user(self.manager_user).action_clear()
        laptop.with_user(self.it_user).action_not_needed()
        self.assertTrue(exit_.is_cleared)
        self.assertFalse(exit_.activity_ids)

        exit_.with_user(self.hr_user).action_done()
        self.assertEqual(exit_.state, 'done')
        departure = exit_.departure_id
        self.assertEqual(departure.departure_date, today - timedelta(days=10))
        self.assertEqual(departure.departure_reason_id, self.env.ref('hr.departure_resigned'))
        self.assertTrue(departure.apply_date, 'the last working day is past: applied at once')
        self.assertFalse(self.employee.active)

    def test_future_departure_and_cancel(self):
        today = fields.Date.context_today(self.env['hr.exit'])
        exit_ = self.resign(date_notice=today, notice_days=30)
        self.approve(exit_)
        exit_.clearance_ids.with_user(self.hr_user).action_clear()
        exit_.with_user(self.hr_user).action_done()
        self.assertFalse(exit_.departure_id.apply_date, 'applied by core HR once the last working day is past')
        self.assertTrue(self.employee.active)
        self.assertEqual(self.employee.contract_date_end, today + timedelta(days=30))

        exit_.with_user(self.hr_user).action_cancel_approved()
        self.assertEqual(exit_.state, 'cancel')
        self.assertFalse(self.employee.departure_id)

    def test_refuse_and_one_at_a_time(self):
        exit_ = self.resign()
        exit_.with_user(self.employee_user).action_submit()
        with self.assertRaises(UserError):
            self.resign().with_user(self.employee_user).action_submit()
        exit_.with_user(self.manager_user).action_approval_refuse('Please stay')
        self.assertEqual(exit_.state, 'refused')
        self.assertFalse(exit_.clearance_ids)

    def test_access(self):
        exit_ = self.resign()
        exit_.with_user(self.employee_user).action_submit()
        colleague = new_test_user(self.env, 'om_exit_colleague', groups='base.group_user')
        self.assertFalse(self.env['hr.exit'].with_user(colleague).search([('id', '=', exit_.id)]))
        self.assertTrue(self.env['hr.exit'].with_user(self.manager_user).search([('id', '=', exit_.id)]))
        exit_.with_user(self.manager_user).action_approval_approve()
        exit_.with_user(self.hr_admin).action_approval_approve()
        self.assertTrue(self.env['hr.exit'].with_user(self.it_user).search([('id', '=', exit_.id)]),
                        'IT sees the exit it clears')
