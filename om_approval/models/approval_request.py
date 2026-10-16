import logging

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
    _order = 'id desc'
    _mail_post_access = 'read'

    name = fields.Char(string='Reference', required=True, readonly=True, copy=False,
                       default=lambda self: self.env._('New'))
    flow_id = fields.Many2one('approval.rule', readonly=True, ondelete='restrict')
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
            line.sudo().write({'state': 'approved', 'user_id': self.env.user.id, 'date': fields.Datetime.now()})
            request.sudo().activity_feedback([ACTIVITY], feedback=self.env._('Approved'))
            request._next()
        return True

    def action_refuse(self, reason=False):
        for request in self:
            line = request._check_approver()
            line.sudo().write({'state': 'refused', 'user_id': self.env.user.id, 'date': fields.Datetime.now(),
                               'note': reason})
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
            line.sudo().state = 'pending'
            for user in line.approver_user_ids:
                self.sudo().activity_schedule(ACTIVITY, summary=self.env._('Approve: %s', self.document_name),
                                              user_id=user.id)
            return
        self.sudo().state = 'approved'
        self.sudo().message_post(body=self.env._('Approved.'), partner_ids=self.requester_id.partner_id.ids)
        self._message_document(self.env._('Approved: %s', self.name))
        self._call_document('_on_approval_approved')
        if self.method and self.flow_id.run_on_approval and self.requester_id != self.env.user:
            self._run_button()

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
