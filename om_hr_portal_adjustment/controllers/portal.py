from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import HrPortal

# the adjustments an employee sees: the drafts and those waiting for approval stay with the payroll
VISIBLE_STATES = ('running', 'done')


class HrPortalAdjustment(HrPortal):

    @http.route('/my/hr/adjustments', type='http', auth='user', website=True)
    def hr_adjustments(self, **kwargs):
        employee = self._employee()
        adjustments = request.env['hr.payroll.adjustment'].sudo().search(
            [('employee_id', '=', employee.id), ('state', 'in', VISIBLE_STATES)])
        return request.render('om_hr_portal_adjustment.portal_my_adjustments', self._values(
            'hr_adjustments', adjustments=adjustments, om_section='Pay Adjustments'))

    @http.route('/my/hr/adjustments/<int:adjustment_id>', type='http', auth='user', website=True)
    def hr_adjustment(self, adjustment_id, **kwargs):
        adjustment = self._own('hr.payroll.adjustment', adjustment_id)
        if adjustment.state not in VISIBLE_STATES:
            raise NotFound()
        return request.render('om_hr_portal_adjustment.portal_my_adjustment', self._values(
            'hr_adjustment', adjustment=adjustment, om_section='Pay Adjustments',
            om_section_url='/my/hr/adjustments', om_record=adjustment.name))
