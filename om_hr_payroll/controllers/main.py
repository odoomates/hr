from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.http.stream import content_disposition


class OmPayslipSelf(http.Controller):

    @http.route('/my/payslip/<int:payslip_id>/pdf', type='http', auth='user')
    def own_payslip_pdf(self, payslip_id, **kwargs):
        """ The PDF of a payslip, for the employee it belongs to only. """
        try:
            payslip = request.env['hr.payslip']._om_own_payslip(payslip_id)
        except AccessError:
            raise NotFound() from None
        pdf, name = payslip._om_render_pdf()
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', content_disposition(name)),
        ])
