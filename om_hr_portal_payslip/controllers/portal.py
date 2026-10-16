from odoo import http
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import HrPortal


class HrPortalPayslip(HrPortal):

    def _payslips(self):
        return request.env['hr.payslip'].sudo().search([
            ('employee_id', '=', self._employee().id), ('state', '=', 'done'), ('credit_note', '=', False)],
            order='date_from desc')

    @http.route('/my/hr/payslips', type='http', auth='user', website=True)
    def hr_payslips(self, **kwargs):
        return request.render('om_hr_portal_payslip.portal_my_payslips', self._values(
            'hr_payslips', payslips=self._payslips(), om_section='Payslips'))

    @http.route('/my/hr/payslips/<int:payslip_id>', type='http', auth='user', website=True)
    def hr_payslip(self, payslip_id, **kwargs):
        payslip = self._own('hr.payslip', payslip_id)
        if payslip.state != 'done' or payslip.credit_note:
            raise request.not_found()
        return request.render('om_hr_portal_payslip.portal_my_payslip', self._values(
            'hr_payslip', payslip=payslip, om_section='Payslips', om_section_url='/my/hr/payslips',
            om_record=payslip.number or payslip.name))
