import base64
import binascii
import hashlib
import secrets
import uuid
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import consteq
from odoo.tools.binary import BinaryBytes
from odoo.tools.mimetypes import guess_mimetype

CODE_MINUTES = 10  # how long an email code stays valid
CODE_ATTEMPTS = 5  # wrong codes before a new one must be asked
CODE_RESEND_SECONDS = 60  # one code a minute at most
SIGNATURE_TYPES = ('image/png', 'image/jpeg', 'image/webp')

# what only the signing itself changes, never a user editing the request
PROTECTED_FIELDS = {'state', 'signed_name', 'signature', 'date_signed', 'decline_reason', 'date_invited',
                    'date_reminded', 'date_opened', 'access_token', 'code_hash', 'code_expiry', 'code_attempts',
                    'code_verified'}


class SignRequestSigner(models.Model):
    """ One person signing a request: their turn, their signature and how they gave it. """
    _name = 'sign.request.signer'
    _description = 'Signer'
    _order = 'sequence, id'
    _rec_name = 'partner_id'

    request_id = fields.Many2one('sign.request', required=True, ondelete='cascade', index=True)
    request_state = fields.Selection(related='request_id.state', string='Request Status')
    sequence = fields.Integer(
        default=10, help='The signers of the same sequence sign together; a higher one waits for the lower ones.')
    role_name = fields.Char(string='Role')
    partner_id = fields.Many2one('res.partner', string='Signer', index=True)
    email = fields.Char(related='partner_id.email')
    state = fields.Selection([
        ('waiting', 'Waiting for Others'),
        ('to_sign', 'To Sign'),
        ('signed', 'Signed'),
        ('declined', 'Declined'),
    ], required=True, default='waiting', copy=False, readonly=True)
    signed_name = fields.Char(string='Signed As', readonly=True, copy=False)
    signature = fields.Image(max_width=1024, max_height=512, readonly=True, copy=False)
    date_signed = fields.Datetime(string='Signed On', readonly=True, copy=False)
    decline_reason = fields.Text(readonly=True, copy=False)
    date_invited = fields.Datetime(string='Asked On', readonly=True, copy=False)
    date_reminded = fields.Datetime(string='Reminded On', readonly=True, copy=False)
    date_opened = fields.Datetime(string='Opened On', readonly=True, copy=False)
    access_token = fields.Char(copy=False, readonly=True, groups='base.group_system')
    code_hash = fields.Char(copy=False, readonly=True, groups='base.group_system')
    code_expiry = fields.Datetime(copy=False, readonly=True, groups='base.group_system')
    code_attempts = fields.Integer(copy=False, readonly=True, groups='base.group_system')
    code_verified = fields.Boolean(string='Email Verified', readonly=True, copy=False)
    is_me = fields.Boolean(compute='_compute_is_me')

    @api.depends_context('uid')
    def _compute_is_me(self):
        for signer in self:
            signer.is_me = signer.partner_id == self.env.user.partner_id

    @api.model_create_multi
    def create(self, vals_list):
        requests = self.env['sign.request'].browse({vals.get('request_id') for vals in vals_list} - {None})
        if not self.env.su and any(request.state != 'draft' for request in requests):
            raise UserError(_('The request is sent: cancel it and send another one to change its signers.'))
        signers = super().create(vals_list)
        for signer in signers.sudo():
            signer.access_token = uuid.uuid4().hex
        return signers

    def write(self, vals):
        if not self.env.su:
            if PROTECTED_FIELDS & set(vals):
                raise UserError(_('A signature is given by its signer, not changed by hand.'))
            if any(signer.request_id.state != 'draft' for signer in self):
                raise UserError(_('The request is sent: cancel it and send another one to change its signers.'))
        return super().write(vals)

    def unlink(self):
        if not self.env.su and any(signer.request_id.state != 'draft' for signer in self):
            raise UserError(_('The request is sent: cancel it and send another one to change its signers.'))
        return super().unlink()

    def _get_sign_url(self):
        self.ensure_one()
        return '%s/sign/%s/%s' % (self.get_base_url(), self.id, self.sudo().access_token)

    def _check_token(self, token):
        self.ensure_one()
        return bool(token) and consteq(self.sudo().access_token or '', token)

    # ------------------------------------------------------------------
    # Notifying
    # ------------------------------------------------------------------

    def _notify(self, template, subject, **values):
        self.ensure_one()
        body = self.env['ir.qweb']._render(template, {
            'signer': self, 'sign_request': self.request_id, 'sign_url': self._get_sign_url(), **values})
        self.request_id.sudo().message_notify(
            partner_ids=self.partner_id.ids, subject=subject, body=body,
            email_layout_xmlid='mail.mail_notification_light')

    def _send_invitation(self, reminder=False):
        self.ensure_one()
        subject = _('Reminder: please sign %s', self.request_id.name) if reminder \
            else _('Please sign %s', self.request_id.name)
        self._notify('om_sign.mail_sign_invitation', subject, reminder=reminder)
        self.env['sign.log']._log(self.request_id, 'reminded' if reminder else 'invited', signer=self)

    # ------------------------------------------------------------------
    # Signing, from the signing page
    # ------------------------------------------------------------------

    def _check_can_sign(self):
        self.ensure_one()
        if self.request_id.state != 'sent':
            raise UserError(_('This request is no longer waiting for signatures.'))
        if self.state != 'to_sign':
            raise UserError(_('It is not your turn to sign yet.') if self.state == 'waiting'
                            else _('You already answered this request.'))

    def _opened(self):
        """ The signer opened the signing page; the first time is logged. """
        self.ensure_one()
        if not self.date_opened and self.state == 'to_sign':
            self.sudo().date_opened = fields.Datetime.now()
            self.env['sign.log']._log(self.request_id, 'opened', signer=self)

    def _needs_code(self):
        self.ensure_one()
        return self.request_id.email_code and not self.code_verified

    @api.model
    def _generate_code(self):
        return '%06d' % secrets.randbelow(10 ** 6)

    def _hash_code(self, code):
        return hashlib.sha256(('%s:%s' % (self.sudo().access_token, code)).encode()).hexdigest()

    def _send_code(self):
        """ Email a new code to the signer. :return: False when one was sent less than a minute ago """
        self.ensure_one()
        self._check_can_sign()
        me = self.sudo()
        now = fields.Datetime.now()
        if me.code_expiry and me.code_expiry - timedelta(minutes=CODE_MINUTES) > \
                now - timedelta(seconds=CODE_RESEND_SECONDS):
            return False
        code = self._generate_code()
        me.write({'code_hash': self._hash_code(code), 'code_attempts': 0,
                  'code_expiry': now + timedelta(minutes=CODE_MINUTES)})
        self._notify('om_sign.mail_sign_code', _('Your code to sign %s', self.request_id.name), code=code,
                     minutes=CODE_MINUTES)
        self.env['sign.log']._log(self.request_id, 'code_sent', signer=self)
        return True

    def _verify_code(self, code):
        """ :return: whether `code` is the one emailed, still valid """
        self.ensure_one()
        self._check_can_sign()
        me = self.sudo()
        if not me.code_hash or me.code_attempts >= CODE_ATTEMPTS or me.code_expiry < fields.Datetime.now():
            return False
        if not consteq(self._hash_code((code or '').strip()), me.code_hash):
            me.code_attempts += 1
            self.env['sign.log']._log(self.request_id, 'code_failed', signer=self)
            return False
        me.write({'code_verified': True, 'code_hash': False})
        self.env['sign.log']._log(self.request_id, 'code_verified', signer=self)
        return True

    def _sign(self, name, signature):
        """ The signer signs as `name` with the image `signature` (base64). """
        self.ensure_one()
        self._check_can_sign()
        if self._needs_code():
            raise UserError(_('Enter the code sent to your email first.'))
        if not (name or '').strip() or not signature:
            raise UserError(_('Write your name and sign.'))
        try:
            image = base64.b64decode(signature, validate=True)
        except (binascii.Error, ValueError, TypeError):
            image = b''
        if guess_mimetype(image) not in SIGNATURE_TYPES:
            raise UserError(_('The signature could not be read. Sign again.'))
        self.sudo().write({
            'signed_name': name.strip(),
            'signature': BinaryBytes(image),
            'state': 'signed',
            'date_signed': fields.Datetime.now(),
        })
        self.env['sign.log']._log(self.request_id, 'signed', signer=self,
                                  document_hash=self.request_id.document_hash)
        self.request_id._activate_next()

    def _decline(self, reason):
        self.ensure_one()
        self._check_can_sign()
        if not (reason or '').strip():
            raise UserError(_('Tell why you decline to sign.'))
        request = self.request_id
        self.sudo().write({'state': 'declined', 'decline_reason': reason.strip()})
        request.sudo().write({'state': 'declined'})
        self.env['sign.log']._log(request, 'declined', signer=self, note=reason.strip())
        request.sudo().message_post(
            body=_('%(signer)s declined to sign: %(reason)s', signer=self.partner_id.name, reason=reason.strip()),
            subtype_xmlid='mail.mt_note', partner_ids=request.requested_by_id.partner_id.ids)
        request._call_host('_on_sign_declined')

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------

    def action_sign(self):
        """ Open the signing page, for a signer who is a user of the backend. """
        self.ensure_one()
        if not self.is_me:
            raise UserError(_('Only %s signs here.', self.partner_id.name))
        return {'type': 'ir.actions.act_url', 'url': self._get_sign_url(), 'target': 'new'}

    def action_send_again(self):
        self.ensure_one()
        self._check_can_sign()
        self.request_id.check_access('write')
        self._send_invitation(reminder=True)
        return True
