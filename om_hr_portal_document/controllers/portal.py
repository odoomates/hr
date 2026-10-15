import base64

from odoo import http
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import OmHrPortal


class OmHrPortalDocument(OmHrPortal):

    @http.route('/my/hr/documents', type='http', auth='user', website=True)
    def om_hr_documents(self, uploaded=None, **kwargs):
        employee = self._om_employee()
        documents = request.env['om.document'].sudo().search([('employee_id', '=', employee.id)],
                                                              order='date_expiry, id')
        return request.render('om_hr_portal_document.portal_my_documents', self._om_values(
            'om_hr_documents', documents=documents, uploaded=uploaded, om_section='Documents'))

    @http.route('/my/hr/documents/<int:document_id>/files/<int:attachment_id>', type='http', auth='user')
    def om_hr_document_file(self, document_id, attachment_id, **kwargs):
        document = self._om_own('om.document', document_id)
        attachment = document.attachment_ids.filtered(lambda a: a.id == attachment_id)
        if not attachment:
            raise request.not_found()
        return request.env['ir.binary']._get_stream_from(attachment.sudo()).get_response(as_attachment=True)

    @http.route('/my/hr/documents/<int:document_id>/upload', type='http', auth='user', website=True,
                methods=['POST'])
    def om_hr_document_upload(self, document_id, **post):
        """ The employee sends the renewed passport or permit: the file is added to the document, and HR checks
            it and updates the dates. """
        document = self._om_own('om.document', document_id)
        upload = post.get('file')
        if upload and getattr(upload, 'filename', None):
            data = upload.read()
            if data:
                request.env['om.document'].sudo().om_board_upload(
                    document.res_model, document.res_id, False, document.id,
                    [{'name': upload.filename, 'mimetype': upload.content_type, 'data': base64.b64encode(data)}])
                document.sudo().message_post(body=request.env._('%s sent a new file from the portal.',
                                                               self._om_employee().name))
        return request.redirect('/my/hr/documents?uploaded=%s' % document.id)
