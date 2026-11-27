from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class OmPlanningRequest(models.Model):
    """ An employee claims an open shift, or swaps a shift with a colleague: the colleague accepts the swap first,
    then it is approved along the approval flow of the shift requests (the manager by default). """
    _name = 'om.planning.request'
    _inherit = ['approval.mixin', 'om.planning.request']

    state = fields.Selection(selection_add=[('draft', 'Draft'), ('to_accept', 'To Accept'), ('pending',)],
                             ondelete={'draft': 'set default', 'to_accept': 'set default'},
                             help='To Accept: the colleague of a swap accepts it, from the backend or the portal, '
                                  'before the approval.')
    # who approves comes from the approval flow
    can_approve = fields.Boolean(compute='_compute_approval_request')
    target_slot_id = fields.Many2one(
        'om.planning.slot', string='Shift Taken', ondelete='cascade', index='btree_not_null',
        help='In a swap, the shift of the colleague the employee takes in exchange.')
    employee_id = fields.Many2one('hr.employee', compute='_compute_employees', store=True, index='btree_not_null',
                                  string='Employee')
    target_employee_id = fields.Many2one('hr.employee', compute='_compute_employees', store=True,
                                         index='btree_not_null', string='Colleague')
    can_accept = fields.Boolean(compute='_compute_can_accept')
    old_request_id = fields.Integer(string='Former Shift Request', readonly=True, copy=False,
                                    index='btree_not_null')

    @api.depends('resource_id.employee_id', 'target_resource_id.employee_id')
    def _compute_employees(self):
        for request in self:
            request.employee_id = request.resource_id.sudo().employee_id[:1]
            request.target_employee_id = request.target_resource_id.sudo().employee_id[:1]

    @api.depends('state', 'approval_state', 'approval_request_ids.state', 'approval_request_ids.line_ids.state')
    @api.depends_context('uid')
    def _compute_approval_request(self):
        """ Along the approval flow; a request without one (asked before the shifts used the planning) as the
            planning decides. """
        super()._compute_approval_request()
        for request in self:
            if request.approval_state == 'draft':
                request.can_approve = request.state == 'pending' and self.env.user in request._planning_approvers()
            else:
                request.can_approve = request.can_approve and request.state == 'pending'

    @api.depends('state', 'target_resource_id')
    @api.depends_context('uid')
    def _compute_can_accept(self):
        for request in self:
            request.can_accept = request.state == 'to_accept' and \
                request.sudo().target_resource_id.user_id == self.env.user

    @api.depends('request_type', 'resource_id', 'slot_id', 'target_slot_id')
    def _compute_name(self):
        super()._compute_name()
        for request in self.filtered('target_slot_id'):
            request.name = self.env._('Swap %(mine)s with %(theirs)s',
                                      mine=request.slot_id._planning_short_label(request.resource_id),
                                      theirs=request.target_slot_id._planning_short_label(request.target_resource_id))

    @api.constrains('request_type', 'target_resource_id', 'slot_id', 'resource_id')
    def _check_request(self):
        # the requests of the former shifts are kept as they were, those decided included
        if self.env.context.get('om_hr_shift_migration'):
            return
        undecided = self.filtered(lambda request: request.state in ('draft', 'to_accept', 'pending'))
        return super(OmPlanningRequest, undecided)._check_request()

    @api.model_create_multi
    def create(self, vals_list):
        migration = self.env.context.get('om_hr_shift_migration')
        for vals in vals_list:
            if vals.get('target_slot_id') and not migration:
                target = self.env['om.planning.slot'].sudo().browse(vals['target_slot_id'])
                vals.setdefault('request_type', 'switch')
                vals.setdefault('target_resource_id', target.employee_id.resource_id.id)
                vals.setdefault('state', 'to_accept')
        requests = super().create(vals_list)
        if not migration:
            requests.filtered(lambda request: request.state != 'draft')._shift_validate()
            requests.filtered(lambda request: request.state == 'to_accept')._shift_notify_colleague()
            requests.filtered(lambda request: request.state == 'pending')._shift_submit_approval()
        return requests

    # ------------------------------------------------------------------
    # Approval flow
    # ------------------------------------------------------------------

    def _planning_approvers(self):
        """ The approvers of the step of the approval flow the request waits for. """
        self.ensure_one()
        if self.approval_state == 'to_approve':
            return self.sudo().approval_request_id.approver_user_ids
        return super()._planning_approvers()

    def _planning_notify_approvers(self):
        """ The approval flow tells its approvers. """
        return None

    def _approval_employee(self):
        self.ensure_one()
        return self.employee_id

    def _approval_check_requester(self):
        for request in self:
            if request.resource_id.user_id != self.env.user and request.create_uid != self.env.user and \
                    not self.env.user.has_group('om_hr_shift.group_shift_planner'):
                raise UserError(self.env._('Only %s or a planner changes the request.', request.resource_id.name))

    def _shift_submit_approval(self):
        """ To the approval, asked by the employee of the request. """
        for request in self:
            requester = request.sudo().resource_id.user_id or self.env.user
            request.with_user(requester).sudo().action_approval_submit()

    def _on_approval_submitted(self, request):
        self.sudo().state = 'pending'

    def _on_approval_approved(self, request):
        result = super()._on_approval_approved(request)
        self.sudo()._shift_apply(self.env.user)
        return result

    def _on_approval_refused(self, request):
        result = super()._on_approval_refused(request)
        self.sudo().write({'state': 'refused', 'approver_id': self.env.uid})
        self.sudo()._planning_notify_requester()
        return result

    def _on_approval_cancelled(self, request):
        result = super()._on_approval_cancelled(request)
        self.sudo().state = 'cancelled'
        return result

    def _on_approval_reset(self):
        self.sudo().state = 'draft'

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def _shift_validate(self):
        for request in self:
            slot = request.slot_id.sudo()
            if slot.state != 'published':
                raise UserError(self.env._('Only a published shift is claimed or swapped.'))
            if request.request_type == 'claim' and not request._shift_can_claim(slot):
                raise UserError(self.env._('The shift %s is for another department or position.',
                                           slot.display_name))
            if request.target_slot_id:
                target = request.target_slot_id.sudo()
                if request.resource_id not in slot.resource_ids:
                    raise UserError(self.env._('Only your own shift is swapped.'))
                if target.state != 'published' or not target.employee_id or \
                        request.resource_id in target.resource_ids:
                    raise UserError(self.env._('Swap with a published shift of a colleague.'))

    def _shift_can_claim(self, slot):
        self.ensure_one()
        employee = self.resource_id.sudo().employee_id[:1]
        if not employee:
            return True
        if slot.department_id and employee.department_id != slot.department_id:
            return False
        if slot.template_id.job_ids and employee.job_id not in slot.template_id.job_ids:
            return False
        return True

    def _shift_notify_colleague(self):
        for request in self.sudo():
            partner = request.target_resource_id._planning_get_partner()
            if partner:
                request.message_notify(
                    partner_ids=partner.ids, subject=self.env._('A swap of shifts for you'),
                    body=self.env._('%(employee)s asks: %(request)s', employee=request.resource_id.name,
                                    request=request.name), subtype_xmlid='mail.mt_note')

    def _shift_apply(self, approver):
        """ The approved request: the shifts change hands, their schedules follow. """
        self._shift_validate()
        for request in self:
            slot = request.slot_id.with_context(om_planning_keep_published=True)
            if request.request_type == 'claim':
                if not slot.is_open:
                    raise UserError(self.env._('The slot %s is already taken.', slot.display_name))
                slot.write({'resource_ids': [Command.link(request.resource_id.id)]})
            elif request.request_type == 'switch':
                slot.write({'resource_ids': [Command.unlink(request.resource_id.id),
                                             Command.link(request.target_resource_id.id)]})
                if request.target_slot_id:
                    request.target_slot_id.with_context(om_planning_keep_published=True).write({
                        'resource_ids': [Command.unlink(request.target_resource_id.id),
                                         Command.link(request.resource_id.id)]})
            else:
                slot.write({'resource_ids': [Command.unlink(request.resource_id.id)]})
            request.write({'state': 'approved', 'approver_id': approver.id})
            request._planning_notify_requester()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_submit(self):
        """ A claim goes to the approval; a swap to the colleague first. """
        drafts = self.filtered(lambda request: request.state == 'draft')
        drafts._approval_check_requester()
        drafts._shift_validate()
        swaps = drafts.filtered('target_slot_id')
        swaps.sudo().state = 'to_accept'
        swaps._shift_notify_colleague()
        (drafts - swaps)._shift_submit_approval()
        return True

    def _shift_check_colleague(self):
        for request in self:
            if request.state != 'to_accept':
                raise UserError(self.env._('%s does not wait for the colleague.', request.name))
            if request.sudo().target_resource_id.user_id != self.env.user and \
                    not self.env.user.has_group('om_hr_shift.group_shift_planner'):
                raise UserError(self.env._('Only %s accepts or declines the swap.',
                                           request.sudo().target_resource_id.name))

    def action_accept(self):
        """ The colleague accepts the swap: it goes to the approval, asked by the employee. """
        self._shift_check_colleague()
        self._shift_validate()
        for request in self:
            request.sudo().message_post(body=self.env._('Accepted by %s.', self.env.user.name),
                                        subtype_xmlid='mail.mt_note')
        self._shift_submit_approval()
        return True

    def action_decline(self):
        self._shift_check_colleague()
        for request in self.sudo():
            request.write({'state': 'refused', 'approval_state': 'refused', 'approver_id': self.env.uid})
            request.message_post(body=self.env._('Declined by %s.', self.env.user.name), subtype_xmlid='mail.mt_note')
            request._planning_notify_requester()
        return True

    def action_approve(self):
        """ Approve the step of the approval flow the request waits for. """
        waiting = self.filtered(lambda request: request.approval_state == 'to_approve')
        if waiting:
            waiting.action_approval_approve()
        if self - waiting:
            return super(OmPlanningRequest, self - waiting).action_approve()
        return True

    def action_refuse(self):
        waiting = self.filtered(lambda request: request.approval_state == 'to_approve')
        if waiting:
            waiting.action_approval_refuse()
        if self - waiting:
            return super(OmPlanningRequest, self - waiting).action_refuse()
        return True

    def action_cancel(self):
        for request in self:
            if request.state not in ('draft', 'to_accept', 'pending'):
                raise UserError(self.env._('Only pending requests can be cancelled.'))
        waiting = self.filtered(lambda request: request.approval_state == 'to_approve')
        waiting.action_approval_cancel()
        others = self - waiting
        others._approval_check_requester()
        others.sudo().write({'state': 'cancelled', 'approval_state': 'cancel'})
        return True
