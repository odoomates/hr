from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import OmHrPortal


class OmHrPortalCertificate(OmHrPortal):

    def _om_certificate_page(self, error=None, form=None):
        employee = self._om_employee()
        certificates = request.env['om.hr.certificate'].sudo().search([('employee_id', '=', employee.id)])
        templates = request.env['om.print.template'].sudo().search([
            ('model', '=', 'hr.employee'), ('employee_request', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id)])
        return request.render('om_hr_portal_certificate.portal_my_certificates', self._om_values(
            'om_hr_certificates', certificates=certificates, templates=templates, error=error, form=form or {},
            om_section='Certificates'))

    @http.route('/my/hr/certificates', type='http', auth='user', website=True)
    def om_hr_certificates(self, **kwargs):
        return self._om_certificate_page()

    @http.route('/my/hr/certificates/new', type='http', auth='user', website=True, methods=['POST'])
    def om_hr_certificate_new(self, **post):
        employee = self._om_employee()
        try:
            template = request.env['om.print.template'].sudo().browse(int(post.get('template_id') or 0)).exists()
            if not template or not template.employee_request or template.model != 'hr.employee':
                raise UserError(request.env._('Choose a certificate.'))
            with request.env.cr.savepoint():
                certificate = request.env['om.hr.certificate'].sudo().create({
                    'employee_id': employee.id,
                    'template_id': template.id,
                    'addressee': post.get('addressee') or False,
                    'purpose': post.get('purpose') or False,
                })
                certificate.action_submit()
        except (UserError, ValidationError, ValueError) as error:
            return self._om_certificate_page(error=str(error.args[0] if error.args else error), form=post)
        return request.redirect('/my/hr/certificates')

    @http.route('/my/hr/certificates/<int:certificate_id>/pdf', type='http', auth='user')
    def om_hr_certificate_pdf(self, certificate_id, **kwargs):
        certificate = self._om_own('om.hr.certificate', certificate_id)
        attachment = certificate.issue_id.attachment_id
        if certificate.state != 'issued' or not attachment or certificate.issue_id.state != 'issued':
            raise request.not_found()
        return request.env['ir.binary']._get_stream_from(attachment.sudo()).get_response(as_attachment=True)
