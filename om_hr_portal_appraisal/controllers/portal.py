from odoo import http
from odoo.http import request
from odoo.tools import html2plaintext, plaintext2html

from odoo.addons.om_hr_portal.controllers.portal import HrPortal


class HrPortalAppraisal(HrPortal):

    @http.route('/my/hr/appraisals', type='http', auth='user', website=True)
    def hr_appraisals(self, **kwargs):
        employee = self._employee()
        appraisals = request.env['hr.appraisal'].sudo().search(
            [('employee_id', '=', employee.id), ('state', '!=', 'cancel')])
        goals = request.env['hr.appraisal.goal'].sudo().search([('employee_id', '=', employee.id)])
        return request.render('om_hr_portal_appraisal.portal_my_appraisals', self._values(
            'hr_appraisals', appraisals=appraisals, goals=goals, om_section='Appraisals'))

    @http.route('/my/hr/appraisals/<int:appraisal_id>', type='http', auth='user', website=True)
    def hr_appraisal(self, appraisal_id, saved=None, **kwargs):
        appraisal = self._own('hr.appraisal', appraisal_id)
        if appraisal.state == 'cancel':
            raise request.not_found()
        # what the employee may read: their own assessment, and the review of the manager once it is done
        return request.render('om_hr_portal_appraisal.portal_my_appraisal', self._values(
            'hr_appraisal', appraisal=appraisal, saved=saved,
            self_text=html2plaintext(appraisal.employee_feedback_html or ''),
            manager_feedback=appraisal.manager_feedback_html if appraisal.state == 'done' else False,
            om_section='Appraisals', om_section_url='/my/hr/appraisals', om_record=appraisal.name))

    @http.route('/my/hr/appraisals/<int:appraisal_id>/save', type='http', auth='user', website=True,
                methods=['POST'])
    def hr_appraisal_save(self, appraisal_id, **post):
        appraisal = self._own('hr.appraisal', appraisal_id)
        if appraisal.state != 'self':
            raise request.not_found()
        appraisal.employee_feedback_html = plaintext2html(post.get('feedback') or '')
        if post.get('submit'):
            appraisal.action_submit_self()
            return request.redirect('/my/hr/appraisals/%s' % appraisal.id)
        return request.redirect('/my/hr/appraisals/%s?saved=1' % appraisal.id)

    @http.route('/my/hr/goals/<int:goal_id>/progress', type='http', auth='user', website=True, methods=['POST'])
    def hr_goal_progress(self, goal_id, **post):
        goal = self._own('hr.appraisal.goal', goal_id)
        progress = max(0, min(100, int(float(post.get('progress') or 0))))
        goal.progress = progress
        return request.redirect('/my/hr/appraisals')
