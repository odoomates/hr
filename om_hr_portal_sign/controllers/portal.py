from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.http.stream import content_disposition

from odoo.addons.om_hr_portal.controllers.portal import HrPortal


class HrPortalSign(HrPortal):

    def _policy_assignments(self):
        """ :return: the policies asked to the employee, those to answer first """
        employee = self._employee()
        return request.env['hr.policy.assignment'].sudo().search(
            [('employee_id', '=', employee.id), ('state', '!=', 'cancelled')]).sorted(
            lambda assignment: (assignment.state != 'pending', -assignment.date_assigned.timestamp()))

    def _policy_page(self, assignment, **values):
        return request.render('om_hr_portal_sign.portal_my_policy', self._values(
            'hr_policy', assignment=assignment, om_section='Policies', om_section_url='/my/hr/policies',
            om_record=assignment.policy_id.name, **values))

    @http.route('/my/hr/policies', type='http', auth='user', website=True)
    def hr_policies(self, **kwargs):
        return request.render('om_hr_portal_sign.portal_my_policies', self._values(
            'hr_policies', assignments=self._policy_assignments(), om_section='Policies'))

    @http.route('/my/hr/policies/<int:assignment_id>', type='http', auth='user', website=True)
    def hr_policy(self, assignment_id, **kwargs):
        assignment = self._own('hr.policy.assignment', assignment_id)
        if assignment.state == 'cancelled':
            raise NotFound()
        signer = assignment._get_signer()
        return self._policy_page(assignment, sign_url=signer and assignment.sign_request_id.state == 'sent'
                                 and signer._get_sign_url())

    @http.route('/my/hr/policies/<int:assignment_id>/document', type='http', auth='user')
    def hr_policy_document(self, assignment_id, **kwargs):
        assignment = self._own('hr.policy.assignment', assignment_id)
        if assignment.content_type != 'pdf' or not assignment.document_file:
            raise NotFound()
        return request.make_response(assignment.document_file.content, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', content_disposition(assignment.document_filename or 'policy.pdf', 'inline')),
            ('X-Content-Type-Options', 'nosniff'),
        ])

    @http.route('/my/hr/policies/<int:assignment_id>/agree', type='http', auth='user', website=True,
                methods=['POST'])
    def hr_policy_agree(self, assignment_id, **post):
        assignment = self._own('hr.policy.assignment', assignment_id)
        try:
            # as the super user, the user still answers: the answer is logged as theirs
            assignment.action_acknowledge()
        except UserError as error:
            return self._policy_page(assignment, error=str(error))
        return request.redirect('/my/hr/policies/%s' % assignment_id)
