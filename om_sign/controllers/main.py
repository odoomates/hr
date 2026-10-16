from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.http.stream import content_disposition

from odoo.addons.portal.controllers.portal import CustomerPortal


class SignPortal(CustomerPortal):
    """ The signing pages. A signer reaches their own signature only, by the secret link emailed to them, logged in
    or not; nothing else is reached by changing an id in the address. """

    def _prepare_portal_counter_values(self, counter):
        if counter == 'sign_count':
            return 'sign.request.signer', self._my_signers_domain(to_sign=True), 'sudo'
        return super()._prepare_portal_counter_values(counter)

    @staticmethod
    def _my_signers_domain(to_sign=False):
        domain = [('partner_id', '=', request.env.user.partner_id.id), ('request_id.state', '!=', 'draft')]
        if to_sign:
            domain += [('state', '=', 'to_sign'), ('request_id.state', '=', 'sent')]
        return domain

    @staticmethod
    def _signer(signer_id, token):
        """ :return: the signer of that id when the token is theirs, as the super user; 404 otherwise """
        signer = request.env['sign.request.signer'].sudo().browse(signer_id).exists()
        if not signer or not signer._check_token(token) or signer.request_id.state == 'draft':
            raise NotFound()
        return signer

    def _page(self, signer, **values):
        return request.render('om_sign.sign_page', {
            'signer': signer,
            'sign_request': signer.request_id,
            'base_url': '/sign/%s/%s' % (signer.id, signer.access_token),
            **values,
        })

    @http.route('/sign/<int:signer_id>/<string:token>', type='http', auth='public', website=True, sitemap=False)
    def sign_page(self, signer_id, token, **kwargs):
        signer = self._signer(signer_id, token)
        signer._opened()
        return self._page(signer)

    @http.route('/sign/<int:signer_id>/<string:token>/document', type='http', auth='public', sitemap=False)
    def sign_document(self, signer_id, token, **kwargs):
        """ The PDF to sign, or the signed one once everyone signed. """
        signer = self._signer(signer_id, token)
        sign_request = signer.request_id
        if sign_request.state == 'signed' and sign_request.signed_attachment_id:
            data, name = sign_request.signed_attachment_id.raw.content, sign_request.signed_attachment_id.name
        else:
            data, name = sign_request._get_document(), sign_request.document_filename or 'document.pdf'
        disposition = 'attachment' if kwargs.get('download') else 'inline'
        return request.make_response(data, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', content_disposition(name, disposition_type=disposition)),
            ('X-Content-Type-Options', 'nosniff'),
        ])

    @http.route('/sign/<int:signer_id>/<string:token>/code', type='http', auth='public', methods=['POST'],
                website=True, sitemap=False)
    def sign_code(self, signer_id, token, code=None, **kwargs):
        """ Send the email code, or check the one entered. """
        signer = self._signer(signer_id, token)
        try:
            if code is None:
                sent = signer._send_code()
                return self._page(signer, message='code_sent' if sent else 'code_wait')
            if not signer._verify_code(code):
                return self._page(signer, error='code_wrong')
        except UserError as error:
            return self._page(signer, error=str(error))
        return request.redirect('/sign/%s/%s' % (signer.id, token))

    @http.route('/sign/<int:signer_id>/<string:token>/accept', type='jsonrpc', auth='public', website=True)
    def sign_accept(self, signer_id, token, name=None, signature=None):
        signer = self._signer(signer_id, token)
        try:
            signer._sign(name, signature)
        except UserError as error:
            return {'error': str(error)}
        return {'force_refresh': True, 'redirect_url': '/sign/%s/%s' % (signer.id, token)}

    @http.route('/sign/<int:signer_id>/<string:token>/decline', type='http', auth='public', methods=['POST'],
                website=True, sitemap=False)
    def sign_decline(self, signer_id, token, reason=None, **kwargs):
        signer = self._signer(signer_id, token)
        try:
            signer._decline(reason)
        except UserError as error:
            return self._page(signer, error=str(error))
        return request.redirect('/sign/%s/%s' % (signer.id, token))

    @http.route('/sign/verify/<string:token>', type='http', auth='public', website=True, sitemap=False)
    def sign_verify(self, token, **kwargs):
        """ The public page the certificate of a signed PDF names: who signed it and its fingerprint. """
        sign_request = request.env['sign.request'].sudo().search(
            [('access_token', '=', token), ('state', '!=', 'draft')], limit=1) if token else None
        return request.render('om_sign.verify_page', {'sign_request': sign_request})

    @http.route('/my/signatures', type='http', auth='user', website=True)
    def my_signatures(self, **kwargs):
        signers = request.env['sign.request.signer'].sudo().search(self._my_signers_domain(), order='id desc')
        return request.render('om_sign.portal_my_signatures', {
            **self._prepare_portal_layout_values(), 'signers': signers, 'page_name': 'signatures'})
