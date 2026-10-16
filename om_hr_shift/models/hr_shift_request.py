from odoo import api, fields, models
from odoo.exceptions import UserError


class HrShiftRequest(models.Model):
    """ An employee claims an open shift, or swaps a shift with a colleague: the colleague accepts, the manager
    approves, along the approval flow of the shift requests. """
    _name = 'hr.shift.request'
    _inherit = ['approval.mixin']
    _description = 'Shift Request'
    _order = 'id desc'
    _mail_post_access = 'read'

    kind = fields.Selection([('claim', 'Claim an Open Shift'), ('swap', 'Swap Shifts')], required=True,
                            default='claim')
    employee_id = fields.Many2one('hr.employee', required=True, index=True,
                                  default=lambda self: self.env.user.employee_id)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    shift_id = fields.Many2one('hr.shift', required=True, ondelete='cascade',
                               help='The open shift claimed, or the shift of the employee given in a swap.')
    target_shift_id = fields.Many2one('hr.shift', string='Shift Taken', ondelete='cascade',
                                      help='The shift of the colleague taken in a swap.')
    target_employee_id = fields.Many2one(related='target_shift_id.employee_id', string='Colleague', store=True)
    note = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'), ('to_accept', 'To Accept'), ('to_approve', 'To Approve'), ('approved', 'Approved'),
        ('refused', 'Refused'), ('cancel', 'Cancelled'),
    ], required=True, default='draft', index=True, tracking=True, copy=False,
        help='To Accept: the colleague of a swap accepts it, from the backend or the portal, before the approval.')
    can_accept = fields.Boolean(compute='_compute_can_accept')

    @api.depends('state', 'target_employee_id')
    @api.depends_context('uid')
    def _compute_can_accept(self):
        for request in self:
            request.can_accept = request.state == 'to_accept' and \
                request.sudo().target_employee_id.user_id == self.env.user

    @api.depends('kind', 'shift_id', 'target_shift_id')
    def _compute_display_name(self):
        for request in self:
            if request.kind == 'swap':
                request.display_name = self.env._('Swap %(mine)s with %(theirs)s', mine=request.shift_id.display_name,
                                                  theirs=request.target_shift_id.display_name)
            else:
                request.display_name = self.env._('Claim %s', request.shift_id.display_name)

    def _validate(self):
        for request in self:
            shift = request.shift_id.sudo()
            if shift.state != 'published':
                raise UserError(self.env._('Only a published shift is claimed or swapped.'))
            if request.kind == 'claim':
                if shift.employee_id:
                    raise UserError(self.env._('The shift %s is no longer open.', shift.display_name))
                if not request._can_claim(shift):
                    raise UserError(self.env._('The shift %s is for another department or position.',
                                               shift.display_name))
            else:
                target = request.target_shift_id.sudo()
                if shift.employee_id != request.employee_id:
                    raise UserError(self.env._('Only your own shift is swapped.'))
                if not target or target.state != 'published' or not target.employee_id or \
                        target.employee_id == request.employee_id:
                    raise UserError(self.env._('Swap with a published shift of a colleague.'))

    def _can_claim(self, shift):
        self.ensure_one()
        employee = self.employee_id.sudo()
        template = shift.template_id
        if shift.department_id and employee.department_id != shift.department_id:
            return False
        if template.job_ids and employee.job_id not in template.job_ids:
            return False
        return True

    def action_submit(self):
        """ A claim goes to the approval; a swap to the colleague first. """
        self._validate()
        swaps = self.filtered(lambda request: request.kind == 'swap')
        for request in swaps:
            request._approval_check_requester()
            request.sudo().state = 'to_accept'
            partner = request.sudo().target_employee_id.user_id.partner_id
            if partner:
                request.sudo().message_notify(
                    partner_ids=partner.ids, subject=self.env._('A swap of shifts for you'),
                    body=self.env._('%(employee)s asks: %(request)s', employee=request.employee_id.name,
                                    request=request.display_name), subtype_xmlid='mail.mt_note')
        if self - swaps:
            (self - swaps).action_approval_submit()
        return True

    def _check_colleague(self):
        for request in self:
            if request.state != 'to_accept':
                raise UserError(self.env._('%s does not wait for the colleague.', request.display_name))
            if request.sudo().target_employee_id.user_id != self.env.user and \
                    not self.env.user.has_group('om_hr_shift.group_shift_planner'):
                raise UserError(self.env._('Only %s accepts or declines the swap.',
                                           request.sudo().target_employee_id.name))

    def action_accept(self):
        """ The colleague accepts the swap: it goes to the approval, asked by the employee. """
        self._check_colleague()
        for request in self:
            request._validate()
            requester = request.sudo().employee_id.user_id or self.env.user
            request.with_user(requester).sudo().action_approval_submit()
            request.message_post(body=self.env._('Accepted by %s.', self.env.user.name), subtype_xmlid='mail.mt_note')
        return True

    def action_decline(self):
        self._check_colleague()
        for request in self:
            request.sudo().write({'state': 'refused', 'approval_state': 'refused'})
            request.message_post(body=self.env._('Declined by %s.', self.env.user.name), subtype_xmlid='mail.mt_note')
        return True

    def _approval_employee(self):
        self.ensure_one()
        return self.employee_id

    def _approval_check_requester(self):
        for request in self:
            if request.employee_id.user_id != self.env.user and \
                    not self.env.user.has_group('om_hr_shift.group_shift_planner'):
                raise UserError(self.env._('Only %s or a planner changes the request.', request.employee_id.name))

    def _on_approval_submitted(self, request):
        self.sudo().state = 'to_approve'

    def _on_approval_approved(self, request):
        result = super()._on_approval_approved(request)
        self.sudo()._apply()
        self.sudo().state = 'approved'
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
        waiting = self.filtered(lambda request: request.state == 'to_accept')
        waiting._approval_check_requester()
        waiting.sudo().write({'state': 'cancel', 'approval_state': 'cancel'})
        others = self - waiting
        if others:
            super(HrShiftRequest, others).action_approval_cancel()
            others.sudo().state = 'cancel'
        return True

    def _apply(self):
        """ The shifts change hands; their schedules follow. """
        self._validate()
        for request in self:
            if request.kind == 'claim':
                request.shift_id.employee_id = request.employee_id
            else:
                mine, theirs = request.shift_id, request.target_shift_id
                colleague = theirs.employee_id
                mine.employee_id = colleague
                theirs.employee_id = request.employee_id
            request.shift_id.message_post(body=self.env._('Changed by the approved request: %s', request.display_name),
                                          subtype_xmlid='mail.mt_note')
