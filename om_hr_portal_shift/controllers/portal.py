from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import HrPortal


class HrPortalShift(HrPortal):

    def _shift_page(self, error=None, form=None, message=None):
        employee = self._employee()
        today = fields.Date.context_today(request.env.user)
        Shift = request.env['hr.shift'].sudo()
        mine = Shift.search([('employee_id', '=', employee.id), ('state', '=', 'published'), ('date', '>=', today)])
        open_shifts = Shift.search([('employee_id', '=', False), ('state', '=', 'published'), ('date', '>=', today),
                                    ('company_id', '=', employee.company_id.id)])
        Request = request.env['hr.shift.request'].sudo()
        claimable = open_shifts.filtered(lambda shift: Request.new({'employee_id': employee.id})._can_claim(shift))
        colleagues = Shift.search([
            ('employee_id', 'not in', [employee.id, False]), ('state', '=', 'published'), ('date', '>=', today),
            ('company_id', '=', employee.company_id.id),
            ('department_id', '=', employee.department_id.id or False)])
        requests = Request.search(['|', ('employee_id', '=', employee.id), ('target_employee_id', '=', employee.id)],
                                  limit=20)
        to_accept = Request.search([('target_employee_id', '=', employee.id), ('state', '=', 'to_accept')])
        unavailable = request.env['hr.shift.unavailability'].sudo().search(
            [('employee_id', '=', employee.id), ('date_to', '>=', today)])
        return request.render('om_hr_portal_shift.portal_my_shifts', self._values(
            'hr_shifts', shifts=mine, open_shifts=claimable, colleague_shifts=colleagues, shift_requests=requests,
            to_accept=to_accept,
            unavailable=unavailable, error=error, message=message, form=form or {}, om_section='Shifts'))

    @http.route('/my/hr/shifts', type='http', auth='user', website=True)
    def hr_shifts(self, **kwargs):
        return self._shift_page()

    def _request(self, values):
        employee = self._employee()
        with request.env.cr.savepoint():
            shift_request = request.env['hr.shift.request'].sudo().create(dict(values, employee_id=employee.id))
            shift_request.action_submit()
        return shift_request

    @http.route('/my/hr/shifts/claim', type='http', auth='user', website=True, methods=['POST'])
    def hr_shift_claim(self, shift_id=None, **post):
        try:
            self._request({'kind': 'claim', 'shift_id': int(shift_id or 0)})
        except (UserError, ValidationError, ValueError) as error:
            return self._shift_page(error=str(error.args[0] if error.args else error))
        return self._shift_page(message=request.env._('Your claim is sent for approval.'))

    @http.route('/my/hr/shifts/swap', type='http', auth='user', website=True, methods=['POST'])
    def hr_shift_swap(self, shift_id=None, target_shift_id=None, **post):
        try:
            mine = self._own('hr.shift', int(shift_id or 0))
            self._request({'kind': 'swap', 'shift_id': mine.id, 'target_shift_id': int(target_shift_id or 0),
                              'note': post.get('note') or False})
        except (UserError, ValidationError, ValueError) as error:
            return self._shift_page(error=str(error.args[0] if error.args else error), form=post)
        return self._shift_page(message=request.env._('Your swap is sent to your colleague.'))

    @http.route('/my/hr/shifts/unavailable', type='http', auth='user', website=True, methods=['POST'])
    def hr_shift_unavailable(self, **post):
        employee = self._employee()
        try:
            with request.env.cr.savepoint():
                request.env['hr.shift.unavailability'].sudo().create({
                    'employee_id': employee.id,
                    'date_from': fields.Date.to_date(post.get('date_from')),
                    'date_to': fields.Date.to_date(post.get('date_to') or post.get('date_from')),
                    'reason': post.get('reason') or False,
                })
        except (UserError, ValidationError, ValueError, TypeError) as error:
            return self._shift_page(error=str(error.args[0] if error.args else error), form=post)
        return request.redirect('/my/hr/shifts')

    @http.route('/my/hr/shifts/unavailable/<int:unavailability_id>/delete', type='http', auth='user', website=True,
                methods=['POST'])
    def hr_shift_unavailable_delete(self, unavailability_id, **post):
        self._own('hr.shift.unavailability', unavailability_id).unlink()
        return request.redirect('/my/hr/shifts')

    @http.route('/my/hr/shifts/requests/<int:request_id>/<any(accept,decline):answer>', type='http', auth='user',
                website=True, methods=['POST'])
    def hr_shift_answer(self, request_id, answer, **post):
        """ The colleague asked for a swap accepts or declines it. """
        shift_request = self._own('hr.shift.request', request_id, employee_field='target_employee_id')
        try:
            # as the super user, still the user answering: the request checks they are the colleague asked
            with request.env.cr.savepoint():
                if answer == 'accept':
                    shift_request.action_accept()
                else:
                    shift_request.action_decline()
        except (UserError, ValidationError) as error:
            return self._shift_page(error=str(error.args[0] if error.args else error))
        return request.redirect('/my/hr/shifts')
