from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrApplicantOffer(models.Model):
    """ The job offered to an applicant: approved, then sent as an offer letter that the company signs first and the
    candidate countersigns. Accepted, it fills the contract of the employee created from the applicant. """
    _name = 'hr.applicant.offer'
    _inherit = ['approval.mixin', 'sign.mixin']
    _description = 'Job Offer'
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, readonly=True, copy=False, default=lambda self: _('New'))
    applicant_id = fields.Many2one('hr.applicant', string='Applicant', required=True, ondelete='cascade', index=True,
                                   tracking=True)
    candidate_name = fields.Char(related='applicant_id.partner_name', string='Candidate')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True,
                                 compute='_compute_company_id', store=True, readonly=False, precompute=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    job_id = fields.Many2one('hr.job', string='Job Position', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', tracking=True)
    wage = fields.Monetary(required=True, tracking=True, help='The monthly gross wage offered.')
    date_start = fields.Date(string='Start Date', required=True, tracking=True)
    employee_type_id = fields.Many2one('hr.employee.type', string='Employee Type', tracking=True)
    resource_calendar_id = fields.Many2one('resource.calendar', string='Working Schedule',
                                           default=lambda self: self.env.company.resource_calendar_id)
    trial_date_end = fields.Date(string='End of Probation')
    benefits = fields.Text(string='Other Benefits', help='Printed in the letter, e.g. housing or a phone.')
    date_valid = fields.Date(string='Valid Until', required=True, tracking=True,
                             default=lambda self: fields.Date.context_today(self) + timedelta(days=7),
                             help='The candidate signs by that day, or the offer expires.')
    template_id = fields.Many2one(
        'print.template', string='Letter', required=True, domain=[('model', '=', 'hr.applicant.offer')],
        default=lambda self: self.env.ref('om_hr_recruitment_offer.print_template_offer_letter',
                                          raise_if_not_found=False))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], required=True, default='draft', copy=False, index=True, tracking=True, readonly=True)
    issue_id = fields.Many2one('print.issue', string='Offer Letter', readonly=True, copy=False)
    sign_request_id = fields.Many2one('sign.request', string='Signature Request', readonly=True, copy=False)
    decline_reason = fields.Text(readonly=True, copy=False)
    date_accepted = fields.Datetime(string='Accepted On', readonly=True, copy=False)

    @api.depends('applicant_id')
    def _compute_company_id(self):
        for offer in self:
            offer.company_id = offer.applicant_id.company_id or offer.company_id or self.env.company

    @api.onchange('applicant_id')
    def _onchange_applicant_id(self):
        applicant = self.applicant_id
        if applicant:
            self.job_id = self.job_id or applicant.job_id
            self.department_id = self.department_id or applicant.department_id
            self.wage = self.wage or applicant.salary_proposed or applicant.salary_expected
            self.date_start = self.date_start or applicant.availability

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.applicant.offer') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        locked = {'applicant_id', 'job_id', 'department_id', 'wage', 'date_start', 'employee_type_id',
                  'resource_calendar_id', 'trial_date_end', 'benefits', 'date_valid', 'template_id'}
        if locked & set(vals) and not self.env.su and any(offer.state != 'draft' for offer in self):
            raise UserError(_('Only a draft offer changes: set it back to draft first.'))
        return super().write(vals)

    def unlink(self):
        if any(offer.state not in ('draft', 'cancelled') for offer in self):
            raise UserError(_('Only a draft or a cancelled offer can be deleted.'))
        return super().unlink()

    # ------------------------------------------------------------------
    # Approval
    # ------------------------------------------------------------------

    def action_submit(self):
        for offer in self:
            if offer.date_valid < fields.Date.context_today(self):
                raise UserError(_('%s is no longer valid: change its Valid Until date.', offer.name))
            if offer.trial_date_end and offer.trial_date_end < offer.date_start:
                raise UserError(_('The probation of %s ends before the start date.', offer.name))
        return self.action_approval_submit()

    def _on_approval_submitted(self, request):
        self.sudo().state = 'to_approve'

    def _on_approval_approved(self, request):
        super()._on_approval_approved(request)
        self.sudo().state = 'approved'

    def _on_approval_refused(self, request):
        super()._on_approval_refused(request)
        self.sudo().state = 'refused'

    def _on_approval_cancelled(self, request):
        super()._on_approval_cancelled(request)
        self.sudo().state = 'cancelled'

    def _on_approval_reset(self):
        self.sudo().state = 'draft'

    def action_approval_cancel(self):
        result = super().action_approval_cancel()
        self.sudo().state = 'cancelled'
        return result

    # ------------------------------------------------------------------
    # Sending and signing
    # ------------------------------------------------------------------

    def _candidate_partner(self):
        """ :return: the contact of the candidate, created from the applicant when it has none, as core does
                     when it creates the employee """
        self.ensure_one()
        applicant = self.applicant_id
        if not applicant.partner_id:
            if not applicant.email_from:
                raise UserError(_('Give the email of %s to send the offer.',
                                  applicant.partner_name or applicant.display_name))
            applicant.partner_id = self.env['res.partner'].create({
                'name': applicant.partner_name or applicant.email_from, 'email': applicant.email_from})
        if not applicant.partner_id.email:
            raise UserError(_('Give the email of %s to send the offer.', applicant.partner_id.name))
        return applicant.partner_id

    def action_send(self):
        """ Issue the offer letter and send it for signature: the company signs first, then the candidate. """
        for offer in self:
            if offer.state != 'approved':
                raise UserError(_('Only an approved offer is sent: %s is not.', offer.name))
            if not offer.template_id.sign_role_ids:
                raise UserError(_('Add the signers to the letter %s first.', offer.template_id.name))
            offer._candidate_partner()
            issue = self.env['print.issue']._create_from_template(offer.template_id, offer.ids)
            issue.action_issue()
            sign_request = self.env['sign.request']._create_for_issue(issue)
            sign_request.write({'date_deadline': offer.date_valid})
            sign_request.action_send()
            offer.sudo().write({'state': 'sent', 'issue_id': issue.id, 'sign_request_id': sign_request.id})
        return True

    def action_cancel(self):
        """ Withdraw a sent offer. """
        for offer in self:
            if offer.state != 'sent':
                raise UserError(_('Only a sent offer is withdrawn: %s is not.', offer.name))
            offer.sign_request_id.action_cancel()
            offer.sudo().state = 'cancelled'
        return True

    def action_reset(self):
        """ A new draft from an offer that was refused, declined, expired or cancelled. """
        self.ensure_one()
        if self.state not in ('refused', 'declined', 'expired', 'cancelled'):
            raise UserError(_('%s is still open.', self.name))
        offer = self.copy({'date_valid': fields.Date.context_today(self) + timedelta(days=7)})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': offer.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }

    def _on_sign_completed(self, sign_request):
        """ The candidate signed: the applicant is hired, with the salary and the start date of the offer. """
        if sign_request != self.sign_request_id or self.state != 'sent':
            return
        self.sudo().write({'state': 'accepted', 'date_accepted': sign_request.date_signed})
        applicant = self.applicant_id.sudo()
        values = {'salary_proposed': self.wage, 'availability': self.date_start}
        hired = applicant._get_hired_stage()
        if hired:
            values['stage_id'] = hired.id
        applicant.write(values)
        applicant.message_post(body=_('%(candidate)s accepted the offer %(offer)s.',
                                      candidate=applicant.partner_name or applicant.display_name, offer=self.name),
                               subtype_xmlid='mail.mt_note')

    def _on_sign_declined(self, sign_request):
        if sign_request != self.sign_request_id or self.state != 'sent':
            return
        signer = sign_request.signer_ids.filtered(lambda s: s.state == 'declined')[:1]
        self.sudo().write({'state': 'declined', 'decline_reason': signer.decline_reason})
        self.applicant_id.sudo().message_post(
            body=_('The offer %(offer)s was declined by %(signer)s: %(reason)s', offer=self.name,
                   signer=signer.partner_id.name, reason=signer.decline_reason),
            subtype_xmlid='mail.mt_note')

    def _on_sign_cancelled(self, sign_request):
        if sign_request != self.sign_request_id or self.state != 'sent':
            return
        self.sudo().state = 'expired' if sign_request.state == 'expired' else 'cancelled'

    # ------------------------------------------------------------------
    # The contract of the employee
    # ------------------------------------------------------------------

    def _employee_values(self):
        """ :return: the contract of the employee created from the applicant, as the offer gave it """
        self.ensure_one()
        values = {
            'wage': self.wage,
            'contract_date_start': self.date_start,
            'date_version': self.date_start,
            'job_id': self.job_id.id,
            'job_title': self.job_id.name,
        }
        if self.department_id:
            values['department_id'] = self.department_id.id
        if self.employee_type_id:
            values['employee_type_id'] = self.employee_type_id.id
        if self.resource_calendar_id:
            values['resource_calendar_id'] = self.resource_calendar_id.id
        if self.trial_date_end:
            values['trial_date_end'] = self.trial_date_end
        return values
