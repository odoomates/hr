from odoo import http
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import HrPortal


class HrPortalAsset(HrPortal):

    @http.route('/my/hr/assets', type='http', auth='user', website=True)
    def hr_assets(self, **kwargs):
        employee = self._employee()
        assignments = request.env['hr.asset.assignment'].sudo().search([('employee_id', '=', employee.id)])
        return request.render('om_hr_portal_asset.portal_my_assets', self._values(
            'hr_assets', assignments=assignments, om_section='Assets'))
