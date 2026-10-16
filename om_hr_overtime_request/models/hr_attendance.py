from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

EPSILON = 1 / 3600


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    overtime_status = fields.Selection([
        ('authorised', 'Authorised'),
        ('pending', 'Not Authorised'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], string='Overtime Approval', readonly=True, copy=False, index='btree_not_null', tracking=True,
        help='Authorised: within the overtime approved in advance. Not Authorised: beyond it, waiting for the '
             'manager, who accepts or rejects it.')

    def _is_overtime(self):
        return self.filtered(lambda a: a.time_rule_id and a.time_rule_id.threshold_operator == 'exceed')

    @api.model_create_multi
    def create(self, vals_list):
        attendances = super().create(vals_list)
        if not self.env.context.get('om_overtime_reviewing'):
            overtime = attendances._is_overtime()
            if overtime:
                self._overtime_review({(a.employee_id, a.date) for a in overtime})
        return attendances

    @staticmethod
    def _hours(attendance):
        return (attendance.check_out - attendance.check_in).total_seconds() / 3600

    @api.model
    def _overtime_review(self, days):
        """ The overtime of each (employee, day) authorised up to the hours approved in advance, an overtime
            crossing the limit split at it; the rest waits for the manager. The overtime the manager decided on is
            left as it is. """
        Attendance = self.sudo().with_context(skip_time_rules=True, tracking_disable=True, om_overtime_reviewing=True)
        Request = self.env['hr.overtime.request'].sudo()
        for employee, day in days:
            if not employee.company_id.overtime_preapproval:
                continue
            overtime = Attendance.search([('employee_id', '=', employee.id), ('date', '=', day),
                                          ('time_rule_id', '!=', False), ('check_out', '!=', False),
                                          ('overtime_status', 'not in', ('accepted', 'rejected'))],
                                         order='check_in, id')._is_overtime()
            overtime = overtime.filtered(lambda a: a.state != 'refused' or a.overtime_status == 'pending')
            allowed = sum(Request.search([('employee_id', '=', employee.id), ('date', '=', day),
                                          ('state', '=', 'approved')]).mapped('hours'))
            used = 0.0
            for attendance in overtime:
                hours = self._hours(attendance)
                if used + hours <= allowed + EPSILON:
                    attendance.write({'overtime_status': 'authorised', 'state': 'validated'})
                    used += hours
                elif used < allowed - EPSILON:
                    split = attendance.check_in + timedelta(hours=allowed - used)
                    rest = attendance.copy_data({'check_in': split, 'check_out': attendance.check_out})[0]
                    attendance.write({'check_out': split, 'overtime_status': 'authorised', 'state': 'validated'})
                    Attendance.create(dict(rest, state='draft', overtime_status='pending',
                                           time_rule_id=attendance.time_rule_id.id,
                                           source_attendance_id=attendance.source_attendance_id.id))
                    used = allowed
                else:
                    attendance.write({'overtime_status': 'pending', 'state': 'draft'})
        return True

    def _check_reviewer(self):
        user = self.env.user
        if user.has_group('hr_attendance.group_hr_attendance_user'):
            return
        if user.has_group('hr_attendance.group_hr_attendance_officer') and all(
                attendance.sudo().employee_id.attendance_manager_id == user
                or attendance.sudo().employee_id.parent_id.user_id == user for attendance in self):
            return
        raise UserError(self.env._('Only the manager or the attendance officers accept or reject overtime.'))

    def action_overtime_accept(self):
        self._check_reviewer()
        pending = self.filtered(lambda a: a.overtime_status == 'pending')
        pending.sudo().with_context(skip_time_rules=True).write({'overtime_status': 'accepted', 'state': 'validated'})
        return True

    def action_overtime_reject(self):
        self._check_reviewer()
        pending = self.filtered(lambda a: a.overtime_status == 'pending')
        pending.sudo().with_context(skip_time_rules=True).write({'overtime_status': 'rejected', 'state': 'refused'})
        return True
