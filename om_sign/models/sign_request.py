import hashlib
import uuid
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools.binary import BinaryBytes
from odoo.tools.image import image_data_uri
from odoo.tools.pdf import merge_pdf

# what only the signing itself changes, never a user editing the request
PROTECTED_FIELDS = {'state', 'document_hash', 'signed_hash', 'signed_attachment_id', 'date_sent', 'date_signed',
                    'access_token', 'reference'}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class SignRequest(models.Model):
    """ A document sent to people to sign: an issued print, or a PDF uploaded.

    The signers sign in their order from a link sent by email, without logging in. Once everyone signed, the
    signed PDF is built: the document with the signatures, followed by a certificate page listing who signed, when
    and from where, and the fingerprint of the document they were sent.
    """
    _name = 'sign.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Signature Request'
    _order = 'id desc'

    name = fields.Char(string='Document', required=True, tracking=True)
    reference = fields.Char(readonly=True, copy=False, default=lambda self: self.env._('New'))
    issue_id = fields.Many2one('print.issue', string='Issued Print', ondelete='restrict', index='btree_not_null',
                               readonly=True)
    res_model = fields.Char(string='Model', index=True, readonly=True)
    res_id = fields.Many2oneReference(string='Record ID', model_field='res_model', index=True, readonly=True)
    res_name = fields.Char(string='Signed For', compute='_compute_res_name')
    document_file = fields.Binary(string='PDF', attachment=True, copy=False,
                                  help='The document to sign, as it is sent to the signers.')
    document_filename = fields.Char(copy=False)
    document_hash = fields.Char(string='Document Fingerprint', readonly=True, copy=False,
                                help='SHA-256 of the document as it was sent: any change to it gives another one.')
    signed_attachment_id = fields.Many2one('ir.attachment', string='Signed PDF', readonly=True, copy=False)
    signed_hash = fields.Char(string='Signed PDF Fingerprint', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Waiting for Signatures'),
        ('signed', 'Signed'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ], required=True, default='draft', copy=False, index=True, tracking=True, readonly=True)
    signer_ids = fields.One2many('sign.request.signer', 'request_id', string='Signers', copy=True)
    log_ids = fields.One2many('sign.log', 'request_id', string='Evidence', readonly=True)
    signer_count = fields.Integer(compute='_compute_progress')
    signed_count = fields.Integer(compute='_compute_progress')
    progress = fields.Char(compute='_compute_progress', string='Signed')
    message = fields.Text(help='Shown to the signers in the email and on the signing page.')
    email_code = fields.Boolean(
        help='Each signer gets a code by email and enters it before signing.')
    date_deadline = fields.Date(string='Sign By', tracking=True)
    reminder_days = fields.Integer(string='Remind Every', default=3,
                                   help='Days between the reminders to a signer. 0 for no reminder.')
    requested_by_id = fields.Many2one('res.users', default=lambda self: self.env.user,
                                      readonly=True, index=True)
    date_sent = fields.Datetime(string='Sent On', readonly=True, copy=False)
    date_signed = fields.Datetime(string='Completed On', readonly=True, copy=False)
    access_token = fields.Char(copy=False, readonly=True, index='btree_not_null', groups='base.group_user')
    company_id = fields.Many2one('res.company', required=True, index=True,
                                 default=lambda self: self.env.company)

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for request in self:
            record = request._get_record()
            request.res_name = record.sudo().display_name if record else False

    @api.depends('signer_ids.state')
    def _compute_progress(self):
        for request in self:
            request.signer_count = len(request.signer_ids)
            request.signed_count = len(request.signer_ids.filtered(lambda signer: signer.state == 'signed'))
            request.progress = '%s / %s' % (request.signed_count, request.signer_count)

    def _get_record(self):
        self.ensure_one()
        if not self.res_model or self.res_model not in self.env or not self.res_id:
            return None
        return self.env[self.res_model].browse(self.res_id).exists() or None

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['access_token'] = uuid.uuid4().hex
            vals['reference'] = self.env['ir.sequence'].sudo().next_by_code('sign.request') or self.env._('New')
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            if PROTECTED_FIELDS & set(vals):
                raise UserError(self.env._('A signature request changes as it is signed, not by hand.'))
            if any(request.state != 'draft' for request in self) and \
                    {'document_file', 'signer_ids', 'name', 'email_code'} & set(vals):
                raise UserError(self.env._('The request is sent: cancel it and send another one to change it.'))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_sent(self):
        if any(request.state != 'draft' for request in self):
            raise UserError(self.env._('Only a draft request can be deleted: cancel a sent one instead.'))

    # ------------------------------------------------------------------
    # Creating
    # ------------------------------------------------------------------

    @api.model
    def _create_for_issue(self, issue):
        """ :return: a draft request to sign the issued print, its signers found from the roles of its template """
        issue.ensure_one()
        if issue.state != 'issued':
            raise UserError(self.env._('Issue %s before sending it for signature.', issue.name))
        template = issue.template_id
        record = issue._get_record()
        signers = [Command.create({
            'sequence': role.sequence,
            'role_name': role.name,
            'partner_id': (role._get_partner(record) if record else role.partner_id).id,
        }) for role in template.sign_role_ids]
        return self.create({
            'name': issue.subject or template.name,
            'issue_id': issue.id,
            'res_model': issue.res_model,
            'res_id': issue.res_id,
            'email_code': template.sign_email_code,
            'reminder_days': template.sign_reminder_days,
            'date_deadline': fields.Date.context_today(self) + timedelta(days=template.sign_validity_days)
                if template.sign_validity_days else False,
            'signer_ids': signers,
            'company_id': issue.company_id.id,
        })

    @api.model
    def _create_for_record(self, record, name=None):
        """ :return: a draft request to sign a PDF about `record`, its signers suggested by the record """
        record.ensure_one()
        defaults = record._sign_default_signers() if hasattr(record, '_sign_default_signers') else []
        signers = [Command.create({'sequence': sequence, 'role_name': role, 'partner_id': partner.id})
                   for sequence, role, partner in defaults]
        company = record.company_id if 'company_id' in record._fields and record.company_id else self.env.company
        return self.create({
            'name': name or record.display_name,
            'res_model': record._name,
            'res_id': record.id,
            'signer_ids': signers,
            'company_id': company.id,
        })

    # ------------------------------------------------------------------
    # Sending and signing
    # ------------------------------------------------------------------

    def _get_document(self):
        """ :return: the bytes of the document to sign """
        self.ensure_one()
        if self.state == 'draft' and self.issue_id:
            raw = self.issue_id.attachment_id.sudo().raw
            return raw.content if raw else b''
        data = self.sudo().document_file
        return data.content if data else b''

    def action_send(self):
        for request in self:
            if request.state != 'draft':
                raise UserError(self.env._('%s is already sent.', request.name))
            if not request.signer_ids:
                raise UserError(self.env._('Add the people signing %s.', request.name))
            missing = request.signer_ids.filtered(lambda signer: not signer.partner_id)
            if missing:
                raise UserError(self.env._('Choose who signs as %s.', missing[0].role_name or self.env._('signer')))
            no_email = request.signer_ids.filtered(lambda signer: not signer.partner_id.email)
            if no_email:
                raise UserError(self.env._('%s has no email address to receive the request.',
                                           no_email[0].partner_id.display_name))
            document = request._get_document()
            if not document:
                raise UserError(self.env._('Add the PDF to sign.'))
            if not request.issue_id and not document.startswith(b'%PDF'):
                raise UserError(self.env._('Only a PDF file can be sent for signature.'))
            values = {'state': 'sent', 'date_sent': fields.Datetime.now(), 'document_hash': sha256(document)}
            if request.issue_id:
                values.update(document_file=BinaryBytes(document),
                              document_filename=request.issue_id.attachment_id.name)
            request.sudo().write(values)
            self.env['sign.log']._log(request, 'sent', document_hash=values['document_hash'])
            request._activate_next()
        return True

    def _activate_next(self):
        """ Ask the next signers, those of the lowest sequence not signed yet; complete when nobody is left. """
        self.ensure_one()
        pending = self.signer_ids.filtered(lambda signer: signer.state in ('waiting', 'to_sign'))
        if not pending:
            return self._complete()
        first = min(pending.mapped('sequence'))
        for signer in pending.filtered(lambda signer: signer.state == 'waiting' and signer.sequence == first):
            signer.sudo().write({'state': 'to_sign', 'date_invited': fields.Datetime.now()})
            signer._send_invitation()
        return True

    def _complete(self):
        """ Everyone signed: build the signed PDF and send it to everyone. """
        self.ensure_one()
        self.sudo().write({'state': 'signed', 'date_signed': fields.Datetime.now()})
        pdf = self._build_signed_pdf()
        attachment = self.env['ir.attachment'].sudo().create({
            'name': self.env._('%s (signed).pdf', (self.document_filename or self.name).removesuffix('.pdf')),
            'raw': pdf,
            'mimetype': 'application/pdf',
            'res_model': self._name,
            'res_id': self.id,
        })
        self.sudo().write({'signed_attachment_id': attachment.id, 'signed_hash': sha256(pdf)})
        self.env['sign.log']._log(self, 'completed', document_hash=self.signed_hash)
        partners = self.signer_ids.partner_id | self.requested_by_id.partner_id
        self.sudo().message_notify(
            partner_ids=partners.ids, subject=self.env._('Signed: %s', self.name), attachment_ids=attachment.ids,
            body=self.env['ir.qweb']._render('om_sign.mail_sign_completed', {'sign_request': self}),
            email_layout_xmlid='mail.mail_notification_light')
        self.sudo().message_post(body=self.env._('Everyone signed. The signed PDF is sent to the signers.'),
                                 subtype_xmlid='mail.mt_note')
        self._call_host('_on_sign_completed')
        return True

    def _build_signed_pdf(self):
        """ :return: the document with the signatures, then the certificate page """
        self.ensure_one()
        report = self.env['ir.actions.report'].sudo()
        if self.issue_id:
            document = report._render_qweb_pdf('om_sign.action_report_sign_document', res_ids=self.ids)[0]
        else:
            page = report._render_qweb_pdf('om_sign.action_report_sign_page', res_ids=self.ids)[0]
            document = self._merge_pdfs([self._get_document(), page])
        audit = report._render_qweb_pdf('om_sign.action_report_sign_audit', res_ids=self.ids)[0]
        return self._merge_pdfs([document, audit])

    @api.model
    def _merge_pdfs(self, parts):
        # the reports are PDF files, except in the tests, where Odoo renders them as HTML that cannot be merged
        if all(part.startswith(b'%PDF') for part in parts):
            return merge_pdf(parts)
        return b''.join(parts)

    def action_cancel(self):
        for request in self:
            if request.state not in ('draft', 'sent'):
                raise UserError(self.env._('%s can no longer be cancelled.', request.name))
            invited = request.signer_ids.filtered(lambda signer: signer.state == 'to_sign')
            request.sudo().write({'state': 'cancelled'})
            if request.date_sent:
                self.env['sign.log']._log(request, 'cancelled')
            for signer in invited:
                signer._notify('om_sign.mail_sign_cancelled', self.env._('No longer to sign: %s', request.name))
            request._call_host('_on_sign_cancelled')
        return True

    @api.model
    def _cron_remind_and_expire(self):
        """ Expire the requests past their deadline, remind the others' signers. """
        today = fields.Date.context_today(self)
        expired = self.search([('state', '=', 'sent'), ('date_deadline', '!=', False),
                               ('date_deadline', '<', today)])
        for request in expired:
            request.sudo().write({'state': 'expired'})
            self.env['sign.log']._log(request, 'expired')
            request.sudo().message_post(
                body=self.env._('The request expired before everyone signed.'), subtype_xmlid='mail.mt_note',
                partner_ids=request.requested_by_id.partner_id.ids)
            request._call_host('_on_sign_cancelled')
        now = fields.Datetime.now()
        signers = self.env['sign.request.signer'].search([
            ('state', '=', 'to_sign'), ('request_id.state', '=', 'sent'), ('request_id.reminder_days', '>', 0)])
        for signer in signers:
            last = signer.date_reminded or signer.date_invited
            if last and last <= now - timedelta(days=signer.request_id.reminder_days):
                signer.sudo().date_reminded = now
                signer._send_invitation(reminder=True)

    def _call_host(self, method):
        """ Tell the record signed for, when it listens (see sign.mixin). """
        record = self._get_record()
        if record is not None and hasattr(record, method):
            getattr(record, method)(self)

    # ------------------------------------------------------------------
    # Printing
    # ------------------------------------------------------------------

    @api.model
    def _signer_entries(self, signers):
        """ :return: what the signature block of each signer shows, for `om_sign.signature_blocks` """
        return [{
            'name': signer.signed_name or signer.partner_id.name,
            'role': signer.role_name,
            'signature': signer.signature,
            'date': signer.date_signed,
        } for signer in signers]

    @api.model
    def _render_signature_blocks(self, entries):
        return self.env['ir.qweb']._render('om_sign.signature_blocks', {
            'entries': entries, 'image_data_uri': image_data_uri})

    def _get_verify_url(self):
        self.ensure_one()
        return '%s/sign/verify/%s' % (self.get_base_url(), self.sudo().access_token)

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------

    def action_download_signed(self):
        self.ensure_one()
        if not self.signed_attachment_id:
            raise UserError(self.env._('%s is not signed by everyone yet.', self.name))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % self.signed_attachment_id.id,
            'target': 'download',
        }

    def action_open_record(self):
        self.ensure_one()
        record = self.issue_id or self._get_record()
        if not record:
            raise UserError(self.env._('The record of %s no longer exists.', self.name))
        return {
            'type': 'ir.actions.act_window',
            'res_model': record._name,
            'res_id': record.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }
