from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import OmHrPortal

# the adjustments an employee sees: the drafts and those waiting for approval stay with the payroll
VISIBLE_STATES = ('running', 'done')


class OmHrPortalAdjustment(OmHrPortal):

    @http.route('/my/hr/adjustments', type='http', auth='user', website=True)
    def om_hr_adjustments(self, **kwargs):
        employee = self._om_employee()
        adjustments = request.env['om.hr.payroll.adjustment'].sudo().search(
            [('employee_id', '=', employee.id), ('state', 'in', VISIBLE_STATES)])
        return request.render('om_hr_portal_adjustment.portal_my_adjustments', self._om_values(
            'om_hr_adjustments', adjustments=adjustments, om_section='Pay Adjustments'))

    @http.route('/my/hr/adjustments/<int:adjustment_id>', type='http', auth='user', website=True)
    def om_hr_adjustment(self, adjustment_id, **kwargs):
        adjustment = self._om_own('om.hr.payroll.adjustment', adjustment_id)
        if adjustment.state not in VISIBLE_STATES:
            raise NotFound()
        return request.render('om_hr_portal_adjustment.portal_my_adjustment', self._om_values(
            'om_hr_adjustment', adjustment=adjustment, om_section='Pay Adjustments',
            om_section_url='/my/hr/adjustments', om_record=adjustment.name))
