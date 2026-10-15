from odoo import http
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import OmHrPortal


class OmHrPortalPayslip(OmHrPortal):

    def _om_payslips(self):
        return request.env['hr.payslip'].sudo().search([
            ('employee_id', '=', self._om_employee().id), ('state', '=', 'done'), ('credit_note', '=', False)],
            order='date_from desc')

    @http.route('/my/hr/payslips', type='http', auth='user', website=True)
    def om_hr_payslips(self, **kwargs):
        return request.render('om_hr_portal_payslip.portal_my_payslips', self._om_values(
            'om_hr_payslips', payslips=self._om_payslips(), om_section='Payslips'))

    @http.route('/my/hr/payslips/<int:payslip_id>', type='http', auth='user', website=True)
    def om_hr_payslip(self, payslip_id, **kwargs):
        payslip = self._om_own('hr.payslip', payslip_id)
        if payslip.state != 'done' or payslip.credit_note:
            raise request.not_found()
        return request.render('om_hr_portal_payslip.portal_my_payslip', self._om_values(
            'om_hr_payslip', payslip=payslip, om_section='Payslips', om_section_url='/my/hr/payslips',
            om_record=payslip.number or payslip.name))
