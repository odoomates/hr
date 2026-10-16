from odoo import api, fields, models
from odoo.exceptions import UserError


class HrCertificate(models.Model):
    """ An employee asks for a certificate, e.g. a salary certificate for a bank: approved along its flow, then
    printed from its template and kept as an issued print the employee downloads. """
    _name = 'hr.certificate'
    _inherit = ['approval.mixin']
    _description = 'Certificate Request'
    _order = 'date desc, id desc'
    _mail_post_access = 'read'

    name = fields.Char(string='Reference', required=True, readonly=True, copy=False,
                       default=lambda self: self.env._('New'))
    employee_id = fields.Many2one(
        'hr.employee', required=True, index=True, tracking=True,
        default=lambda self: self.env.user.employee_id)
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        compute='_compute_company_id', store=True, readonly=False, precompute=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    template_id = fields.Many2one(
        'print.template', string='Certificate', required=True, tracking=True,
        domain="[('model', '=', 'hr.employee'), ('employee_request', '=', True), "
               "'|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    addressee = fields.Char(help='Who the certificate is for, e.g. the name of a bank or an embassy. '
                                 'Leave empty for "To Whom It May Concern".')
    purpose = fields.Text(help='Why the certificate is needed.')
    date = fields.Date(string='Asked On', required=True, default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('issued', 'Issued'),
        ('refused', 'Refused'),
        ('cancel', 'Cancelled'),
    ], required=True, default='draft', copy=False, index=True, tracking=True)
    issue_id = fields.Many2one('print.issue', string='Print', readonly=True, copy=False)
    issue_name = fields.Char(related='issue_id.name', string='Certificate Reference')

    @api.depends('employee_id')
    def _compute_company_id(self):
        for certificate in self:
            certificate.company_id = certificate.employee_id.company_id or certificate.company_id \
                or self.env.company

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', self.env._('New')) == self.env._('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.certificate') or self.env._('New')
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_submitted(self):
        if any(certificate.state not in ('draft', 'cancel') for certificate in self):
            raise UserError(self.env._('Only a draft or a cancelled certificate request can be deleted.'))

    def action_submit(self):
        for certificate in self:
            if certificate.state != 'draft':
                raise UserError(self.env._('Only a draft can be submitted: %s is not.', certificate.name))
            if not certificate.template_id.employee_request:
                raise UserError(self.env._('%s is not a certificate employees request.', certificate.template_id.name))
        return self.action_approval_submit()

    def _approval_employee(self):
        self.ensure_one()
        return self.employee_id

    def _approval_check_requester(self):
        self.ensure_one()
        if self.employee_id.user_id != self.env.user and not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(self.env._('Only %(employee)s or HR can change %(request)s.',
                                       employee=self.employee_id.name, request=self.name))

    def _on_approval_submitted(self, request):
        self.sudo().state = 'to_approve'

    def _on_approval_approved(self, request):
        result = super()._on_approval_approved(request)
        self._issue()
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

    def _issue(self):
        """ Print the certificate as the super user: it shows the wage, which the employee cannot read, from a
            template only HR writes. """
        for certificate in self.sudo():
            values = {'date': fields.Date.context_today(certificate)}
            if certificate.addressee:
                values['addressee'] = certificate.addressee
            issue = self.env['print.issue'].sudo()._create_from_template(
                certificate.template_id, certificate.employee_id.ids, values)
            issue.action_issue()
            certificate.write({'issue_id': issue.id, 'state': 'issued'})
            certificate.message_post(
                body=self.env._('%(certificate)s is ready: %(reference)s.', certificate=certificate.template_id.name,
                                reference=issue.name),
                partner_ids=certificate.employee_id.user_id.partner_id.ids,
                message_type='comment', subtype_xmlid='mail.mt_comment')

    def action_download(self):
        self.ensure_one()
        if not self.issue_id:
            raise UserError(self.env._('%s is not printed yet.', self.name))
        return self.issue_id.action_download()
