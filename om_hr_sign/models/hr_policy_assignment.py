from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.http import request as http_request
from odoo.tools.binary import BinaryBytes

# what only the answer itself changes, never a user editing the line
PROTECTED_FIELDS = {'state', 'date_done', 'done_by_id', 'ip', 'user_agent', 'sign_request_id', 'date_reminded',
                    'problem', 'version_id', 'employee_id'}


class HrPolicyAssignment(models.Model):
    """ A version of a policy asked to an employee, and their answer: agreed with one click, or signed. """
    _name = 'hr.policy.assignment'
    _inherit = ['sign.mixin']
    _description = 'Policy Answer'
    _order = 'date_assigned desc, id desc'

    version_id = fields.Many2one('hr.policy.version', required=True, ondelete='cascade', index=True, readonly=True)
    policy_id = fields.Many2one(related='version_id.policy_id', store=True, index=True)
    answer_type = fields.Selection(related='policy_id.answer_type')
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', index=True, readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True, string='Department')
    company_id = fields.Many2one(related='version_id.company_id', store=True, index=True)
    state = fields.Selection([
        ('pending', 'To Answer'),
        ('done', 'Answered'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
    ], required=True, default='pending', readonly=True, index=True)
    date_assigned = fields.Datetime(string='Asked On', required=True, default=fields.Datetime.now, readonly=True)
    date_due = fields.Date(string='Due', readonly=True)
    date_done = fields.Datetime(string='Answered On', readonly=True)
    is_overdue = fields.Boolean(compute='_compute_is_overdue', search='_search_is_overdue', string='Overdue')
    done_by_id = fields.Many2one('res.users', string='Answered By', readonly=True)
    ip = fields.Char(string='IP Address', readonly=True)
    user_agent = fields.Char(string='Browser', readonly=True)
    sign_request_id = fields.Many2one('sign.request', string='Signature Request', readonly=True)
    sign_state = fields.Selection(related='sign_request_id.state', string='Signature')
    date_reminded = fields.Datetime(string='Reminded On', readonly=True)
    problem = fields.Char(readonly=True, help='Why the employee could not be asked, e.g. no email address.')
    # the content of the version, for the employee reading it
    content_type = fields.Selection(related='version_id.content_type')
    body = fields.Html(related='version_id.body')
    document_file = fields.Binary(related='version_id.document_file')
    document_filename = fields.Char(related='version_id.document_filename')

    @api.depends('policy_id', 'employee_id')
    def _compute_display_name(self):
        for assignment in self:
            assignment.display_name = '%s: %s' % (assignment.policy_id.name, assignment.employee_id.name)

    @api.depends('state', 'date_due')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for assignment in self:
            assignment.is_overdue = assignment.state == 'pending' and bool(assignment.date_due) and \
                assignment.date_due < today

    def _search_is_overdue(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise UserError(_('Search Overdue with = or != and a boolean.'))
        today = fields.Date.context_today(self)
        if (operator == '=') == value:
            return [('state', '=', 'pending'), ('date_due', '<', today)]
        return ['|', ('state', '!=', 'pending'), '|', ('date_due', '=', False), ('date_due', '>=', today)]

    def write(self, vals):
        if PROTECTED_FIELDS & set(vals) and not self.env.su:
            raise UserError(_('An answer to a policy is given by the employee, not changed by hand.'))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Asking
    # ------------------------------------------------------------------

    def _start(self):
        """ Ask the employees: by email for an agreement, through a signature request for a signature. """
        for assignment in self:
            if assignment.answer_type == 'sign':
                assignment._send_sign_request()
            else:
                assignment._notify()

    def _send_sign_request(self):
        self.ensure_one()
        partner = self.employee_id.work_contact_id
        if not partner.email:
            self.sudo().problem = _('%s has no work email to receive the signature request.', self.employee_id.name)
            return
        version = self.version_id
        sign_request = self.env['sign.request'].sudo().create({
            'name': version.name,
            'document_file': BinaryBytes(version._get_pdf()),
            'document_filename': '%s.pdf' % version.name,
            'res_model': self._name,
            'res_id': self.id,
            'reminder_days': self.policy_id.remind_days,
            'date_deadline': self.date_due,
            'company_id': self.company_id.id,
            'signer_ids': [(0, 0, {'role_name': _('Employee'), 'partner_id': partner.id})],
        })
        sign_request.action_send()
        self.sudo().write({'sign_request_id': sign_request.id, 'problem': False, 'state': 'pending'})

    def _get_my_url(self):
        """ :return: where the employee answers, when they are a user of the backend """
        self.ensure_one()
        user = self.employee_id.user_id
        if not user or user.share:
            return False
        return '%s/odoo/action-om_hr_sign.hr_policy_assignment_action_my/%s' % (self.get_base_url(), self.id)

    def _notify(self, reminder=False):
        self.ensure_one()
        partner = self.employee_id.work_contact_id
        if not partner:
            return
        name = self.policy_id.name
        subject = _('Reminder: %s', name) if reminder else _('To read and agree: %s', name)
        body = self.env['ir.qweb']._render('om_hr_sign.mail_policy_assigned', {
            'assignment': self, 'reminder': reminder, 'url': self._get_my_url()})
        self.policy_id.sudo().message_notify(partner_ids=partner.ids, subject=subject, body=body,
                                             email_layout_xmlid='mail.mail_notification_light')

    @api.model
    def _cron_remind(self):
        """ Remind the employees who did not agree yet; Sign reminds those who sign. """
        now = fields.Datetime.now()
        for assignment in self.search([('state', '=', 'pending'), ('answer_type', '=', 'acknowledge'),
                                       ('policy_id.remind_days', '>', 0)]):
            last = assignment.date_reminded or assignment.date_assigned
            if last <= now - timedelta(days=assignment.policy_id.remind_days):
                assignment.sudo().date_reminded = now
                assignment._notify(reminder=True)

    def _cancel(self):
        for assignment in self.sudo():
            assignment.state = 'cancelled'
            if assignment.sign_request_id.state in ('draft', 'sent'):
                assignment.sign_request_id.action_cancel()

    # ------------------------------------------------------------------
    # Answering
    # ------------------------------------------------------------------

    def action_acknowledge(self):
        """ The employee agrees to the policy. """
        for assignment in self:
            if not self.env.su and assignment.employee_id.user_id != self.env.user:
                raise UserError(_('Only %s answers this policy.', assignment.employee_id.name))
            if assignment.answer_type != 'acknowledge':
                raise UserError(_('%s is to be signed.', assignment.policy_id.name))
            if assignment.state != 'pending':
                raise UserError(_('This policy is no longer waiting for your answer.'))
            values = {'state': 'done', 'date_done': fields.Datetime.now(), 'done_by_id': self.env.uid}
            if http_request:
                values.update(ip=http_request.httprequest.remote_addr,
                              user_agent=(http_request.httprequest.headers.get('User-Agent') or '')[:256])
            assignment.sudo().write(values)
        return True

    def _get_signer(self):
        self.ensure_one()
        return self.sign_request_id.signer_ids.filtered(
            lambda signer: signer.partner_id == self.employee_id.work_contact_id)[:1]

    def action_sign(self):
        """ Open the signing page, for an employee who is a user of the backend. """
        self.ensure_one()
        if self.employee_id.user_id != self.env.user:
            raise UserError(_('Only %s signs this policy.', self.employee_id.name))
        signer = self._get_signer()
        if self.state != 'pending' or self.sign_request_id.state != 'sent' or not signer:
            raise UserError(_('This policy is not waiting for your signature.'))
        return {'type': 'ir.actions.act_url', 'url': signer.sudo()._get_sign_url(), 'target': 'new'}

    def action_send_again(self):
        """ HR asks again an employee who declined, or whose request expired or could not be sent. """
        for assignment in self:
            if assignment.answer_type != 'sign' or assignment.state not in ('pending', 'declined') or \
                    assignment.sign_request_id.state in ('sent', 'signed'):
                raise UserError(_('%s is already waiting for a signature or answered.', assignment.display_name))
            assignment._send_sign_request()
        return True

    def action_cancel(self):
        self.filtered(lambda assignment: assignment.state in ('pending', 'declined'))._cancel()
        return True

    # ------------------------------------------------------------------
    # The signature request telling how it ended
    # ------------------------------------------------------------------

    def _on_sign_completed(self, sign_request):
        if sign_request == self.sign_request_id and self.state == 'pending':
            self.sudo().write({'state': 'done', 'date_done': sign_request.date_signed})

    def _on_sign_declined(self, sign_request):
        if sign_request == self.sign_request_id and self.state == 'pending':
            self.sudo().write({'state': 'declined'})
