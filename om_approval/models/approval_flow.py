from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools.safe_eval import safe_eval


def _literal_domain(env, domain):
    return Domain(safe_eval(domain or '[]', {'context': env.context, 'user': env.user}))


class ApprovalFlow(models.Model):
    """ Who approves, in which order, before a button of a model runs or before a document is approved. """
    _name = 'approval.rule'
    _description = 'Approval Flow'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade', index=True,
                               domain=[('transient', '=', False)])
    model = fields.Char(related='model_id.model', store=True, string='Model Name')
    is_document = fields.Boolean(compute='_compute_is_document')
    button_id = fields.Many2one(
        'approval.button', ondelete='cascade', domain="[('model_id', '=', model_id)]",
        help='The button stopped until the approval is given. Leave it empty on a document approved by its own '
             'Submit button, such as an HR request.')
    method = fields.Char(related='button_id.method', store=True, index=True)
    company_id = fields.Many2one('res.company', help='Empty: the flow applies to every company.')
    domain = fields.Char(
        string='Applies To', default='[]',
        help='The records the flow applies to, e.g. the sale orders above 10,000. The first matching flow is used.')
    step_ids = fields.One2many('approval.step', 'flow_id', string='Steps', copy=True)
    fallback_group_id = fields.Many2one(
        'res.groups', string='Approvers When Nobody Is Found',
        default=lambda self: self.env.ref('om_approval.group_approval_manager', raise_if_not_found=False),
        help='Approve a step finding nobody, e.g. an employee without a manager.')
    self_approve = fields.Boolean(
        string='Requester Approves His Steps', default=True,
        help='The steps the requester is an approver of are approved as he asks, e.g. a sales manager confirming '
             'his own order. Otherwise somebody else approves them.')
    run_on_approval = fields.Boolean(
        string='Run the Button Once Approved', default=True,
        help='Once approved, the button runs as the requester. Otherwise the requester clicks it again.')
    note = fields.Text(string='Message to the Requester', translate=True,
                       help='Shown when the button is stopped, e.g. "Orders above 10,000 need the approval of the '
                            'sales director."')

    @api.depends('model')
    def _compute_is_document(self):
        documents = set(self.env['approval.mixin']._inherit_children)
        for flow in self:
            flow.is_document = flow.model in documents

    @api.constrains('model_id', 'button_id')
    def _check_button_model(self):
        for flow in self:
            if flow.button_id and flow.button_id.model_id != flow.model_id:
                raise ValidationError(self.env._('The button of the flow %s belongs to another model.', flow.name))
            if not flow.button_id and not flow.is_document:
                raise ValidationError(self.env._(
                    'Choose the button the flow %(flow)s stops: %(model)s has no approval of its own.',
                    flow=flow.name, model=flow.model_id.name))

    @api.onchange('model_id')
    def _onchange_model_id(self):
        if self.model_id:
            self.env['approval.button']._sync(self.model_id.model)
        if self.button_id.model_id != self.model_id:
            self.button_id = False

    def action_refresh_buttons(self):
        for flow in self:
            self.env['approval.button']._sync(flow.model)
        return True

    @api.model
    def _get_flow(self, record, method=False):
        """ :return: the first active flow of `record` for the button `method`, or for the document itself when
                     no method is given, matching the record; or an empty recordset """
        flows = self.sudo().search([
            ('model', '=', record._name),
            ('method', '=', method or False),
            ('company_id', 'in', [False, self._record_company(record).id]),
        ])
        for flow in flows:
            if record.sudo().filtered_domain(_literal_domain(self.env, flow.domain)):
                return flow
        return flows.browse()

    @api.model
    def _record_company(self, record):
        if 'company_id' in record._fields and record.company_id:
            return record.company_id
        return self.env.company

    @api.model
    def _has_button_flows(self, model, method):
        """ Quick test made on every button click, before reading the records. """
        return bool(self.sudo().search_count([('model', '=', model), ('method', '=', method)], limit=1))


class ApprovalStep(models.Model):
    """ One approval of a flow, and who gives it. """
    _name = 'approval.step'
    _description = 'Approval Step'
    _order = 'sequence, id'

    flow_id = fields.Many2one('approval.rule', required=True, ondelete='cascade', index=True)
    model = fields.Char(related='flow_id.model')
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True)
    approver_type = fields.Selection([
        ('user', 'Given Users'),
        ('group', 'Users of a Group'),
        ('field', 'User of a Field'),
    ], string='Approver', required=True, default='group')
    group_id = fields.Many2one('res.groups')
    user_ids = fields.Many2many('res.users', string='Users')
    field_path = fields.Char(
        string='Field', help='The field of the record naming the approver, e.g. user_id for the salesperson of a sale '
                             'order, or team_id.user_id for the leader of its sales team.')
    domain = fields.Char(
        string='Only When', default='[]',
        help='The step is skipped for the records outside this domain, e.g. an amount above a threshold.')
    remind_days = fields.Integer(string='Remind After', help='Days before the approvers are reminded, then again '
                                                             'every as many days. 0 for no reminder.')
    escalate_days = fields.Integer(string='Escalate After', help='Days before other users are asked to decide '
                                                                 'too. 0 for no escalation.')
    escalate_type = fields.Selection([
        ('fallback', 'Fallback Group of the Flow'),
        ('user', 'Given Users'),
        ('group', 'Users of a Group'),
    ], string='Escalate To', required=True, default=lambda self: self._default_escalate_type())
    escalate_user_ids = fields.Many2many('res.users', 'approval_step_escalate_user_rel', string='Escalation Users')
    escalate_group_id = fields.Many2one('res.groups', string='Escalation Group')

    @api.constrains('approver_type', 'group_id', 'user_ids', 'field_path')
    def _check_approver(self):
        for step in self:
            if step.approver_type == 'group' and not step.group_id:
                raise ValidationError(self.env._('Choose the group approving the step %s.', step.name))
            if step.approver_type == 'user' and not step.user_ids:
                raise ValidationError(self.env._('Choose the users approving the step %s.', step.name))
            if step.approver_type == 'field':
                step._check_field_path()

    def _check_field_path(self):
        self.ensure_one()
        model = self.env[self.flow_id.model]
        try:
            for name in (self.field_path or '').split('.'):
                model = self.env[model._fields[name].comodel_name]
        except (KeyError, AttributeError):
            raise ValidationError(self.env._('%(path)s is not a field path of %(model)s.',
                                             path=self.field_path, model=self.flow_id.model_id.name)) from None
        if model._name not in self._users_models():
            raise ValidationError(self.env._('The field %s must lead to users, employees or contacts.',
                                             self.field_path))

    @api.model
    def _users_models(self):
        return ('res.users', 'res.partner')

    def _applies_to(self, record):
        self.ensure_one()
        return bool(record.sudo().filtered_domain(_literal_domain(self.env, self.domain)))

    def _get_approvers(self, request, record):
        """ :return: the users approving the step for `record`, or the fallback group of the flow when nobody is
                     found. Unless the requester approves his own steps, the users `request` excludes, i.e. the
                     requester, approve only when nobody else can. """
        self.ensure_one()
        users = getattr(self, f'_approvers_{self.approver_type}')(request, record.sudo())
        users = users.filtered(lambda user: user.active and not user.share)
        if self.flow_id.self_approve:
            return users or self._fallback_approvers(request)
        excluded = request._excluded_approvers()
        fallback = self._fallback_approvers(request)
        return (users - excluded) or (fallback - excluded) or fallback

    def _approvers_user(self, request, record):
        return self.user_ids

    def _approvers_group(self, request, record):
        return self.group_id.all_user_ids

    def _approvers_field(self, request, record):
        return self._as_users(record.mapped(self.field_path))

    @api.model
    def _as_users(self, records):
        if records._name == 'res.partner':
            return records.user_ids
        return records if records._name == 'res.users' else self.env['res.users']

    def _fallback_approvers(self, request):
        return request._fallback_approvers(self.flow_id.fallback_group_id)

    @api.model
    def _default_escalate_type(self):
        return 'fallback'

    def _escalation_users(self, line):
        """ :return: the users asked to decide a step waiting too long """
        self.ensure_one()
        users = getattr(self, f'_escalate_{self.escalate_type}')(line)
        return users.filtered(lambda user: user.active and not user.share) or \
            self._escalate_fallback(line)

    def _escalate_fallback(self, line):
        return line.request_id._fallback_approvers(self.flow_id.fallback_group_id)

    def _escalate_user(self, line):
        return self.escalate_user_ids

    def _escalate_group(self, line):
        return self.escalate_group_id.all_user_ids
