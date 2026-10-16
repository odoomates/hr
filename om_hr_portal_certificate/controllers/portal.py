from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import HrPortal


class HrPortalCertificate(HrPortal):

    def _certificate_page(self, error=None, form=None):
        employee = self._employee()
        certificates = request.env['hr.certificate'].sudo().search([('employee_id', '=', employee.id)])
        templates = request.env['print.template'].sudo().search([
            ('model', '=', 'hr.employee'), ('employee_request', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id)])
        return request.render('om_hr_portal_certificate.portal_my_certificates', self._values(
            'hr_certificates', certificates=certificates, templates=templates, error=error, form=form or {},
            om_section='Certificates'))

    @http.route('/my/hr/certificates', type='http', auth='user', website=True)
    def hr_certificates(self, **kwargs):
        return self._certificate_page()

    @http.route('/my/hr/certificates/new', type='http', auth='user', website=True, methods=['POST'])
    def hr_certificate_new(self, **post):
        employee = self._employee()
        try:
            template = request.env['print.template'].sudo().browse(int(post.get('template_id') or 0)).exists()
            if not template or not template.employee_request or template.model != 'hr.employee':
                raise UserError(request.env._('Choose a certificate.'))
            with request.env.cr.savepoint():
                certificate = request.env['hr.certificate'].sudo().create({
                    'employee_id': employee.id,
                    'template_id': template.id,
                    'addressee': post.get('addressee') or False,
                    'purpose': post.get('purpose') or False,
                })
                certificate.action_submit()
        except (UserError, ValidationError, ValueError) as error:
            return self._certificate_page(error=str(error.args[0] if error.args else error), form=post)
        return request.redirect('/my/hr/certificates')

    @http.route('/my/hr/certificates/<int:certificate_id>/pdf', type='http', auth='user')
    def hr_certificate_pdf(self, certificate_id, **kwargs):
        certificate = self._own('hr.certificate', certificate_id)
        attachment = certificate.issue_id.attachment_id
        if certificate.state != 'issued' or not attachment or certificate.issue_id.state != 'issued':
            raise request.not_found()
        return request.env['ir.binary']._get_stream_from(attachment.sudo()).get_response(as_attachment=True)
