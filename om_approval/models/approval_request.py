import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ACTIVITY = 'om_approval.mail_act_approval'


class ApprovalRequest(models.Model):
    """ The approval a record waits for: for a button of the record, or for the record itself when it is a
        document with an approval of its own. Its lines are the steps of the flow, approved in turn. """
    _name = 'approval.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Approval Request'
    _check_company_auto = True
    _order = 'id desc'
    _mail_post_access = 'read'

    name = fields.Char(string='Reference', required=True, readonly=True, copy=False,
                       default=lambda self: self.env._('New'))
    flow_id = fields.Many2one('approval.rule', readonly=True, ondelete='restrict', check_company=True)
    res_model = fields.Char(string='Model', required=True, readonly=True, index=True)
    res_id = fields.Many2oneReference(string='Record ID', model_field='res_model', required=True, readonly=True,
                                      index=True)
    model_name = fields.Char(string='Kind of Record', compute='_compute_model_name')
    document_name = fields.Char(string='Record', compute='_compute_document_name')
    method = fields.Char(string='Button Method', readonly=True)
    button_name = fields.Char(string='Button', readonly=True)
    requester_id = fields.Many2one('res.users', string='Requested By', required=True, readonly=True, index=True,
                                   default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', readonly=True, index=True)
    state = fields.Selection([
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('refused', 'Refused'),
        ('cancel', 'Cancelled'),
    ], required=True, default='to_approve', readonly=True, index=True, tracking=True,
        help='Done: the button ran once approved.')
    line_ids = fields.One2many('approval.line', 'request_id', string='Approvals', readonly=True)
    approval_step = fields.Char(string='Waiting For', compute='_compute_current')
    approver_user_ids = fields.Many2many('res.users', string='Approvers', compute='_compute_current',
                                         search='_search_approver_user_ids')
    can_approve = fields.Boolean(compute='_compute_current')
    note = fields.Text(string='Message', related='flow_id.note')

    @api.depends('res_model')
    def _compute_model_name(self):
        for request in self:
            request.model_name = self.env['ir.model']._get(request.res_model).name if request.res_model else False

    @api.depends('res_model', 'res_id')
    def _compute_document_name(self):
        for request in self:
            record = request._record()
            request.document_name = record.display_name if record else self.env._('Deleted record')

    @api.depends('state', 'line_ids.state', 'line_ids.approver_user_ids')
    @api.depends_context('uid')
    def _compute_current(self):
        is_admin = self.env.user.has_group('om_approval.group_approval_manager')
        for request in self:
            line = request._pending_line()
            request.approval_step = line.name
            request.approver_user_ids = line.approver_user_ids
            request.can_approve = bool(line) and (self.env.user in line.approver_user_ids or is_admin)

    def _search_approver_user_ids(self, operator, value):
        return [('state', '=', 'to_approve'),
                ('line_ids', 'any', [('state', '=', 'pending'), ('approver_user_ids', operator, value)])]

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    @api.model
    def _request(self, record, flow, method=False, button_name=False):
        """ Ask for the approval of `record` along `flow`.

        :return: the request, already approved when no step applies or when the requester approves them all
        """
        request = self.sudo().create({
            'name': self.env['ir.sequence'].sudo().next_by_code('approval.request') or self.env._('New'),
            'flow_id': flow.id or False,
            'res_model': record._name,
            'res_id': record.id,
            'method': method,
            'button_name': button_name,
            'requester_id': self.env.user.id,
            'company_id': self.env['approval.rule']._record_company(record).id,
        })
        request._create_lines(record, flow)
        request._message_document(self.env._('Approval asked: %s', request.name))
        request._next()
        return request

    @api.model
    def _gate_button(self, model, method, ids):
        """ Decide whether the button `method` of the records `ids` of `model` may run.

        A record a flow applies to runs once its request for the button is approved; that request is then done.
        Otherwise the click asks for the approval, or reminds that it was already asked for.

        :return: None when the button may run, or the action telling the user why it did not
        """
        flows = self.env['approval.rule']
        records = self.env[model].browse(ids).exists()
        blocked = []
        for record in records:
            flow = flows._get_flow(record, method)
            if not flow:
                continue
            requests = self.sudo().search([
                ('res_model', '=', model), ('res_id', '=', record.id), ('method', '=', method),
                ('state', 'in', ('to_approve', 'approved')),
            ], order='id desc')
            approved = requests.filtered(lambda r: r.state == 'approved')[:1]
            if approved:
                approved.state = 'done'
                continue
            if requests:
                blocked.append((record, requests[0], False))
                continue
            request = self._request(record, flow, method=method, button_name=flow.button_id.name)
            if request.state == 'approved':
                request.sudo().state = 'done'
                continue
            blocked.append((record, request, True))
        if not blocked:
            return None
        lines = []
        for record, request, new in blocked:
            line = self.env._('%(record)s: approval asked (%(request)s), waiting for %(step)s.') if new \
                else self.env._('%(record)s: still waiting for %(step)s (%(request)s).')
            lines.append(line % {'record': record.display_name, 'request': request.name,
                                 'step': request.approval_step})
        note = blocked[0][1].flow_id.note
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._('Approval needed'),
                'message': '\n'.join(([note] if note else []) + lines),
                'type': 'warning',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    def _create_lines(self, record, flow):
        """ One line per step of `flow` applying to the record. The approvers are decided now, so that a later
            change, e.g. of a manager, does not move an approval already asked for. """
        self.ensure_one()
        values = []
        for step in flow.step_ids.filtered(lambda s: s._applies_to(record)):
            approvers = step._get_approvers(self, record)
            vals = {'request_id': self.id, 'step_id': step.id, 'sequence': step.sequence, 'name': step.name,
                    'approver_user_ids': approvers.ids}
            if flow.self_approve and self.requester_id in approvers:
                vals.update(state='approved', user_id=self.requester_id.id, date=fields.Datetime.now(),
                            note=self.env._('Approved by the requester, an approver of the step.'))
            values.append(vals)
        if not flow.step_ids:
            fallback = self._fallback_approvers(flow.fallback_group_id)
            values.append({'request_id': self.id, 'sequence': 10, 'name': self.env._('Approval'),
                           'approver_user_ids': ((fallback - self._excluded_approvers()) or fallback).ids})
        self.env['approval.line'].sudo().create(values)

    def _fallback_approvers(self, group):
        """ The users approving a step finding nobody: `group`, by default the approval administrators. """
        group = group or self.env.ref('om_approval.group_approval_manager')
        return group.all_user_ids.filtered(lambda user: user.active and not user.share)

    def _excluded_approvers(self):
        """ The users who do not approve the request when somebody else can. """
        self.ensure_one()
        return self.requester_id

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------

    def action_approve(self):
        for request in self:
            line = request._check_approver()
            line.sudo().write({'state': 'approved', 'user_id': self.env.user.id, 'date': fields.Datetime.now(),
                               'note': line._on_behalf_note()})
            request.sudo().activity_feedback([ACTIVITY], feedback=self.env._('Approved'))
            request._next()
        return True

    def action_refuse(self, reason=False):
        for request in self:
            line = request._check_approver()
            line.sudo().write({'state': 'refused', 'user_id': self.env.user.id, 'date': fields.Datetime.now(),
                               'note': '\n'.join(filter(None, [line._on_behalf_note(), reason]))})
            request.line_ids.filtered(lambda line: line.state == 'waiting').sudo().state = 'cancel'
            request.sudo().activity_unlink([ACTIVITY])
            request.sudo().state = 'refused'
            message = self.env._('Refused by %(user)s at the step %(step)s: %(reason)s', user=self.env.user.name,
                                 step=line.name, reason=reason or self.env._('no reason given'))
            request.sudo().message_post(body=message, partner_ids=request.requester_id.partner_id.ids)
            request._message_document(message)
            request._call_document('_on_approval_refused')
        return True

    def action_open_refuse(self):
        self.ensure_one()
        self._check_approver()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Refuse'),
            'res_model': 'approval.refuse',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_cancel(self):
        """ Withdraw the request. The approvals given so far stay, cancelled. """
        for request in self:
            if request.state not in ('to_approve', 'approved'):
                raise UserError(self.env._('%s can no longer be cancelled.', request.name))
            if self.env.user != request.requester_id and not self.env.user.has_group(
                    'om_approval.group_approval_manager'):
                raise UserError(self.env._('Only %(user)s, who asked, can cancel %(request)s.',
                                           user=request.requester_id.name, request=request.name))
            request.line_ids.filtered(lambda line: line.state in ('waiting', 'pending')).sudo().state = 'cancel'
            request.sudo().activity_unlink([ACTIVITY])
            request.sudo().state = 'cancel'
            request._call_document('_on_approval_cancelled')
        return True

    def action_open_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _pending_line(self):
        self.ensure_one()
        if self.state != 'to_approve':
            return self.env['approval.line']
        return self.line_ids.filtered(lambda line: line.state == 'pending')[:1]

    def _next(self):
        """ Ask the approvers of the next step, or approve the request when no step is left. """
        self.ensure_one()
        lines = self.line_ids.sorted(lambda line: (line.sequence, line.id))
        line = lines.filtered(lambda line: line.state == 'waiting')[:1]
        if line:
            line.sudo().write({'state': 'pending', 'date_pending': fields.Datetime.now()})
            for user in line.approver_user_ids:
                self._schedule_approval(user)
            line._apply_delegations()
            return
        self.sudo().state = 'approved'
        self.sudo().message_post(body=self.env._('Approved.'), partner_ids=self.requester_id.partner_id.ids)
        self._message_document(self.env._('Approved: %s', self.name))
        self._call_document('_on_approval_approved')
        if self.method and self.flow_id.run_on_approval and self.requester_id != self.env.user:
            self._run_button()

    def _schedule_approval(self, user):
        self.ensure_one()
        self.sudo().activity_schedule(ACTIVITY, summary=self.env._('Approve: %s', self.document_name),
                                      user_id=user.id)

    def _run_button(self):
        """ Run the approved button as the requester. A failure, e.g. a record changed meanwhile, leaves the request
            approved, for the requester to click the button again. """
        self.ensure_one()
        record = self._record()
        if not record:
            return
        try:
            with self.env.cr.savepoint():
                self.sudo().state = 'done'
                getattr(record.with_user(self.requester_id).with_company(self.company_id or self.env.company),
                        self.method)()
        except Exception as error:  # whatever the button raises is reported to the requester
            _logger.info('om_approval: %s could not run %s on %s: %s', self.name, self.method, record, error)
            self.sudo().message_post(
                body=self.env._('Approved, but %(button)s could not run: %(error)s. Click the button again.',
                                button=self.button_name or self.method, error=error),
                partner_ids=self.requester_id.partner_id.ids)

    def _check_approver(self):
        self.ensure_one()
        line = self._pending_line()
        if not line:
            raise UserError(self.env._('%s is not waiting for an approval.', self.name))
        if self.env.user not in line.approver_user_ids and not self.env.user.has_group(
                'om_approval.group_approval_manager'):
            raise UserError(self.env._('You are not an approver of %(request)s at the step %(step)s.',
                                       request=self.name, step=line.name))
        return line

    # ------------------------------------------------------------------
    # The record
    # ------------------------------------------------------------------

    def _record(self):
        self.ensure_one()
        if not self.res_model or self.res_model not in self.env:
            return None
        return self.env[self.res_model].sudo().browse(self.res_id).exists() or None

    def _call_document(self, hook):
        """ Tell a document with an approval of its own about the decision. """
        record = self._record()
        if record is not None and not self.method and hasattr(record, hook):
            getattr(record, hook)(self)

    def _message_document(self, body):
        record = self._record()
        if record is not None and hasattr(record, 'message_post'):
            record.message_post(body=body, subtype_xmlid='mail.mt_note')


class ApprovalLine(models.Model):
    """ One step of a request, and its decision. """
    _name = 'approval.line'
    _description = 'Approval'
    _order = 'request_id, sequence, id'

    request_id = fields.Many2one('approval.request', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='request_id.company_id', store=True, index=True)
    step_id = fields.Many2one('approval.step', ondelete='set null')
    sequence = fields.Integer()
    name = fields.Char(string='Approval', required=True)
    approver_user_ids = fields.Many2many('res.users', string='Approvers')
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Cancelled'),
    ], required=True, default='waiting', index=True)
    user_id = fields.Many2one('res.users', string='Decided By')
    date = fields.Datetime(string='Decided On')
    note = fields.Text()
    date_pending = fields.Datetime(string='Asked On', readonly=True)
    substitutes = fields.Json(readonly=True, help='The substitutes added, by user id: the names they stand for.')
    date_reminded = fields.Datetime(string='Reminded On', readonly=True)
    date_escalated = fields.Datetime(string='Escalated On', readonly=True)

    # ------------------------------------------------------------------
    # Substitutes and escalation
    # ------------------------------------------------------------------

    def _add_approvers(self, users, message):
        """ Let `users` decide the step too: they get the activity, the request says why. """
        self.ensure_one()
        request = self.request_id
        if not request.flow_id.self_approve:
            users -= request._excluded_approvers()
        users -= self.approver_user_ids
        if not users:
            return users
        self.sudo().approver_user_ids = [(4, user.id) for user in users]
        for user in users:
            request._schedule_approval(user)
        request.sudo().message_post(body=message, subtype_xmlid='mail.mt_note', partner_ids=users.partner_id.ids)
        return users

    def _apply_delegations(self):
        """ Add the substitutes of the approvers away today. """
        Delegation = self.env['approval.delegation']
        for line in self.filtered(lambda line: line.state == 'pending'):
            found = Delegation._substitutes(line.approver_user_ids, line.request_id.flow_id)
            substitutes = dict(line.substitutes or {})
            for delegate, stands_for in found.items():
                message = self.env._('%(delegate)s approves %(step)s for %(users)s, away.', delegate=delegate.name,
                                     step=line.name, users=', '.join(stands_for.mapped('name')))
                if line._add_approvers(delegate, message):
                    substitutes[str(delegate.id)] = stands_for.mapped('name')
            if substitutes != (line.substitutes or {}):
                line.sudo().substitutes = substitutes

    def _on_behalf_note(self):
        """ :return: the note of a decision taken by a substitute """
        self.ensure_one()
        names = (self.substitutes or {}).get(str(self.env.user.id))
        return self.env._('On behalf of %s.', ', '.join(names)) if names else False

    @api.model
    def _cron_follow_up(self):
        """ Every day: the substitutes of the approvers away from today, the reminders, the escalations. """
        lines = self.sudo().search([('state', '=', 'pending'), ('request_id.state', '=', 'to_approve')])
        lines._apply_delegations()
        now = fields.Datetime.now()
        for line in lines.filtered('step_id'):
            step = line.step_id
            asked = line.date_pending or line.create_date
            if step.escalate_days and not line.date_escalated and asked <= now - timedelta(days=step.escalate_days):
                users = step._escalation_users(line)
                line._add_approvers(users, self.env._('%(step)s is waiting since %(days)s days: %(users)s asked to '
                                                      'decide too.', step=line.name, days=step.escalate_days,
                                                      users=', '.join(users.mapped('name'))))
                line.sudo().date_escalated = now
            elif step.remind_days and (line.date_reminded or asked) <= now - timedelta(days=step.remind_days):
                line.request_id.sudo().message_post(
                    body=self.env._('Reminder: %(step)s is waiting for your decision.', step=line.name),
                    subtype_xmlid='mail.mt_note', partner_ids=line.approver_user_ids.partner_id.ids)
                line.sudo().date_reminded = now
