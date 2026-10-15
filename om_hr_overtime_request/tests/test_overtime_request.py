from datetime import date, datetime

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged

DAY = date(2026, 6, 9)


@tagged('post_install', '-at_install')
class TestOvertimeRequest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.om_overtime_preapproval = True
        cls.manager_user = new_test_user(cls.env, 'om_ot_manager',
                                         groups='base.group_user,hr_attendance.group_hr_attendance_officer')
        cls.employee_user = new_test_user(cls.env, 'om_ot_employee', groups='base.group_user')
        calendar = cls.env['resource.calendar'].create({
            'name': 'OT 8-17', 'attendance_ids': [
                Command.create({'dayofweek': str(day), 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'})
                for day in range(5)] + [
                Command.create({'dayofweek': str(day), 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
                for day in range(5)]})
        manager = cls.env['hr.employee'].create({'name': 'OT Manager', 'user_id': cls.manager_user.id})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'OT Employee', 'tz': 'UTC', 'user_id': cls.employee_user.id, 'parent_id': manager.id,
            'attendance_manager_id': cls.manager_user.id, 'resource_calendar_id': calendar.id,
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1)})
        cls.employee.version_id.resource_calendar_id = calendar
        cls.env['hr.time.rule'].search([]).write({'active': False})
        cls.overtime_type = cls.env['hr.work.entry.type'].create({'name': 'OT Overtime', 'code': 'OMOTREQ'})
        cls.rule = cls.env['hr.time.rule'].create({
            'name': 'Daily Overtime (Pre-Approval Test)', 'calendar_source': 'employee', 'quantity_period': 'day',
            'work_entry_type_id': cls.overtime_type.id,
            'condition_work_entry_type_ids': [(4, cls.env.company._get_default_attendance_work_entry_type().id)],
        })

    def request(self, hours):
        request = self.env['om.hr.overtime.request'].with_user(self.employee_user).create(
            {'employee_id': self.employee.id, 'date': DAY, 'hours': hours, 'reason': 'Month end'})
        request.action_submit()
        return request

    def work_twelve_hours(self):
        self.env['hr.attendance'].create({'employee_id': self.employee.id, 'check_in': datetime(2026, 6, 9, 7, 0),
                                          'check_out': datetime(2026, 6, 9, 19, 0), 'state': 'validated'})

    def overtime(self):
        return self.env['hr.attendance'].search([('employee_id', '=', self.employee.id),
                                                 ('time_rule_id', '=', self.rule.id)], order='check_in')

    def summary(self):
        return [(round((a.check_out - a.check_in).total_seconds() / 3600, 2), a.state, a.om_overtime_status)
                for a in self.overtime()]

    def test_not_authorised_waits(self):
        self.work_twelve_hours()
        self.assertEqual(sum(h for h, _state, _status in self.summary()), 4.0)
        self.assertEqual({(state, status) for _h, state, status in self.summary()}, {('draft', 'pending')},
                         'nothing approved in advance: it all waits')

    def test_authorised_in_advance_and_split(self):
        request = self.request(3)
        self.assertEqual((request.state, request.approver_user_ids), ('to_approve', self.manager_user))
        request.with_user(self.manager_user).action_approval_approve()
        self.work_twelve_hours()
        authorised = sum(h for h, state, status in self.summary() if status == 'authorised' and state == 'validated')
        pending = sum(h for h, state, status in self.summary() if status == 'pending' and state == 'draft')
        self.assertEqual((authorised, pending), (3.0, 1.0), 'split at the approved hours')

    def test_approved_afterwards(self):
        self.work_twelve_hours()
        request = self.request(5)
        request.with_user(self.manager_user).action_approval_approve()
        self.assertEqual({status for _h, _state, status in self.summary()}, {'authorised'},
                         'approved later: the waiting overtime is authorised')
        request.with_user(self.manager_user).action_approval_cancel()
        self.assertEqual({status for _h, _state, status in self.summary()}, {'pending'}, 'withdrawn: it waits again')

    def test_manager_accepts(self):
        self.work_twelve_hours()
        overtime = self.overtime()
        with self.assertRaises(UserError):
            overtime.with_user(self.employee_user).action_om_overtime_accept()
        overtime.with_user(self.manager_user).action_om_overtime_accept()
        self.assertEqual({(state, status) for _h, state, status in self.summary()}, {('validated', 'accepted')})
        self.request(1).with_user(self.manager_user).action_approval_approve()
        self.assertEqual({status for _h, _state, status in self.summary()}, {'accepted'},
                         'a decision of the manager stays')

    def test_manager_rejects(self):
        self.work_twelve_hours()
        self.overtime().with_user(self.manager_user).action_om_overtime_reject()
        self.assertEqual({(state, status) for _h, state, status in self.summary()}, {('refused', 'rejected')})
        self.request(2).with_user(self.manager_user).action_approval_approve()
        self.assertEqual({status for _h, _state, status in self.summary()}, {'rejected'})

    def test_without_preapproval(self):
        self.env.company.om_overtime_preapproval = False
        self.work_twelve_hours()
        self.assertEqual({(state, status) for _h, state, status in self.summary()}, {('validated', False)})

    def test_team_officer_reaches_the_menus(self):
        """ An officer managing only their team, not all the attendances, reviews the overtime of their team. """
        self.assertFalse(self.manager_user.has_group('hr_attendance.group_hr_attendance_user'))
        visible = self.env['ir.ui.menu'].with_user(self.manager_user)._visible_menu_ids()
        for xmlid in ('menu_om_overtime', 'menu_om_overtime_review', 'menu_om_overtime_requests'):
            self.assertIn(self.env.ref('om_hr_overtime_request.' + xmlid).id, visible, xmlid)
