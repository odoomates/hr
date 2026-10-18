from odoo import http
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import HrPortal


class HrPortalPayslip(HrPortal):

    def _payslips(self):
        return request.env['hr.payslip'].sudo().search([
            ('employee_id', '=', self._employee().id), ('state', '=', 'done'), ('credit_note', '=', False)],
            order='date_from desc')

    def _statement_years(self, payslips):
        """ :return: the payroll years of the payslips, latest first, as (year, label): 2026, or 2026-2027 for a
            payroll year from April to March """
        Payslip = request.env['hr.payslip']
        years = {}
        for payslip in payslips:
            date_from = Payslip._get_year_start(payslip.date_to, payslip.company_id)
            date_to = Payslip._get_tax_year(date_from.year, payslip.company_id)[1]
            years[date_from.year] = str(date_from.year) if date_from.year == date_to.year \
                else '%s-%s' % (date_from.year, date_to.year)
        return sorted(years.items(), reverse=True)

    @http.route('/my/hr/payslips', type='http', auth='user', website=True)
    def hr_payslips(self, **kwargs):
        payslips = self._payslips()
        return request.render('om_hr_portal_payslip.portal_my_payslips', self._values(
            'hr_payslips', payslips=payslips, statement_years=self._statement_years(payslips),
            om_section='Payslips'))

    @http.route('/my/hr/payslips/<int:payslip_id>', type='http', auth='user', website=True)
    def hr_payslip(self, payslip_id, **kwargs):
        payslip = self._own('hr.payslip', payslip_id)
        if payslip.state != 'done' or payslip.credit_note:
            raise request.not_found()
        return request.render('om_hr_portal_payslip.portal_my_payslip', self._values(
            'hr_payslip', payslip=payslip, om_section='Payslips', om_section_url='/my/hr/payslips',
            om_record=payslip.number or payslip.name))
