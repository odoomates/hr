from odoo import http
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import OmHrPortal


class OmHrPortalAsset(OmHrPortal):

    @http.route('/my/hr/assets', type='http', auth='user', website=True)
    def om_hr_assets(self, **kwargs):
        employee = self._om_employee()
        assignments = request.env['om.hr.asset.assignment'].sudo().search([('employee_id', '=', employee.id)])
        return request.render('om_hr_portal_asset.portal_my_assets', self._om_values(
            'om_hr_assets', assignments=assignments, om_section='Assets'))
