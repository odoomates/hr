from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    overtime_preapproval = fields.Boolean(
        string='Overtime Needs Pre-Approval',
        help='Overtime beyond the hours approved in advance waits for the manager to accept or reject it.')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    overtime_preapproval = fields.Boolean(related='company_id.overtime_preapproval', readonly=False)


class HrOvertimeRequest(models.Model):
    """ Overtime authorised in advance: asked by the employee or by the manager, approved along its flow. The
    overtime of the day is accepted up to the approved hours. """
    _name = 'hr.overtime.request'
    _inherit = ['approval.mixin']
    _description = 'Overtime Request'
    _check_company_auto = True
    _order = 'date desc, id desc'
    _mail_post_access = 'read'

    employee_id = fields.Many2one('hr.employee', required=True, index=True,
                                  default=lambda self: self.env.user.employee_id, check_company=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    date = fields.Date(required=True, index=True, default=fields.Date.context_today)
    hours = fields.Float(required=True, default=1.0)
    reason = fields.Char(required=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Approved'),
        ('refused', 'Refused'), ('cancel', 'Cancelled'),
    ], required=True, default='draft', index=True, tracking=True, copy=False)

    @api.depends('employee_id', 'date', 'hours')
    def _compute_display_name(self):
        for request in self:
            request.display_name = self.env._('%(employee)s, %(hours)s h on %(date)s',
                                              employee=request.employee_id.name, hours=request.hours, date=request.date)

    @api.constrains('hours')
    def _check_hours(self):
        for request in self:
            if not 0 < request.hours <= 24:
                raise ValidationError(self.env._('The overtime asked for is between 0 and 24 hours.'))

    def action_submit(self):
        return self.action_approval_submit()

    def _approval_employee(self):
        self.ensure_one()
        return self.employee_id

    def _approval_check_requester(self):
        for request in self:
            employee = request.sudo().employee_id
            if employee.user_id != self.env.user and employee.parent_id.user_id != self.env.user and \
                    not self.env.user.has_group('hr_attendance.group_hr_attendance_officer'):
                raise UserError(self.env._('Only %s, their manager or the attendance officers ask for their overtime.',
                                           employee.name))

    def _on_approval_submitted(self, request):
        self.sudo().state = 'to_approve'

    def _on_approval_approved(self, request):
        result = super()._on_approval_approved(request)
        self.sudo().state = 'approved'
        self.env['hr.attendance']._overtime_review({(r.employee_id, r.date) for r in self.sudo()})
        return result

    def _on_approval_refused(self, request):
        result = super()._on_approval_refused(request)
        self.sudo().state = 'refused'
        return result

    def _on_approval_cancelled(self, request):
        result = super()._on_approval_cancelled(request)
        self.sudo().state = 'cancel'
        return result

    def _on_approval_reset(self):
        self.sudo().state = 'draft'

    def action_approval_cancel(self):
        approved = self.filtered(lambda request: request.state == 'approved')
        if approved:
            if not self.env.user.has_group('hr_attendance.group_hr_attendance_officer'):
                raise UserError(self.env._('An approved overtime is withdrawn by the attendance officers.'))
            approved.sudo().write({'state': 'cancel', 'approval_state': 'cancel'})
            self.env['hr.attendance']._overtime_review({(r.employee_id, r.date) for r in approved.sudo()})
        others = self - approved
        if others:
            super(HrOvertimeRequest, others).action_approval_cancel()
            others.sudo().state = 'cancel'
        return True
