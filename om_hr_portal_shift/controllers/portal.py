from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from werkzeug.exceptions import NotFound

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import HrPortal


class HrPortalShift(HrPortal):

    @staticmethod
    def _shift_label(shift):
        """ The day and hours of a shift in the timezone of its employee, and its template. """
        start, stop = shift._shift_local(shift.start_datetime), shift._shift_local(shift.end_datetime)
        label = '%s, %s-%s' % (start.strftime('%a %d %b'), start.strftime('%H:%M'), stop.strftime('%H:%M'))
        return '%s %s' % (label, shift.template_id.name) if shift.template_id else label

    def _shift_page(self, error=None, form=None, message=None):
        employee = self._employee()
        resource = employee.resource_id
        today = fields.Date.context_today(request.env.user)
        Shift = request.env['om.planning.slot'].sudo()
        mine = Shift.search([('resource_ids', 'in', resource.ids), ('state', '=', 'published'),
                             ('shift_date', '>=', today)])
        open_shifts = Shift.search([('is_open', '=', True), ('state', '=', 'published'), ('shift_date', '>=', today),
                                    ('company_id', '=', employee.company_id.id)])
        Request = request.env['om.planning.request'].sudo()
        claimable = open_shifts.filtered(
            lambda shift: Request.new({'resource_id': resource.id})._shift_can_claim(shift))
        colleagues = Shift.search([
            ('resource_ids', '!=', False), ('resource_ids', 'not in', resource.ids), ('state', '=', 'published'),
            ('shift_date', '>=', today), ('company_id', '=', employee.company_id.id),
            ('department_id', '=', employee.department_id.id or False)])
        requests = Request.search(['|', ('resource_id', '=', resource.id), ('target_resource_id', '=', resource.id)],
                                  limit=20)
        to_accept = Request.search([('target_resource_id', '=', resource.id), ('state', '=', 'to_accept')])
        unavailable = request.env['resource.calendar.leaves'].sudo().search([
            ('resource_id', '=', resource.id), ('shift_unavailability', '=', True),
            ('date_to', '>=', fields.Datetime.now())])
        return request.render('om_hr_portal_shift.portal_my_shifts', self._values(
            'hr_shifts', shifts=mine, open_shifts=claimable, colleague_shifts=colleagues, shift_requests=requests,
            to_accept=to_accept, unavailable=unavailable, shift_label=self._shift_label, error=error,
            message=message, form=form or {}, om_section='Shifts'))

    @http.route('/my/hr/shifts', type='http', auth='user', website=True)
    def hr_shifts(self, **kwargs):
        return self._shift_page()

    def _request(self, values):
        employee = self._employee()
        with request.env.cr.savepoint():
            shift_request = request.env['om.planning.request'].sudo().create(
                dict(values, resource_id=employee.resource_id.id))
        return shift_request

    @http.route('/my/hr/shifts/claim', type='http', auth='user', website=True, methods=['POST'])
    def hr_shift_claim(self, shift_id=None, **post):
        try:
            shift = request.env['om.planning.slot'].sudo().browse(int(shift_id or 0)).exists()
            if not shift or shift.company_id != self._employee().company_id:
                raise UserError(request.env._('This shift is not open to you.'))
            self._request({'request_type': 'claim', 'slot_id': shift.id})
        except (UserError, ValidationError, ValueError) as error:
            return self._shift_page(error=str(error.args[0] if error.args else error))
        return self._shift_page(message=request.env._('Your claim is sent for approval.'))

    @http.route('/my/hr/shifts/swap', type='http', auth='user', website=True, methods=['POST'])
    def hr_shift_swap(self, shift_id=None, target_shift_id=None, **post):
        try:
            mine = request.env['om.planning.slot'].sudo().browse(int(shift_id or 0)).exists()
            if not mine or self._employee().resource_id not in mine.resource_ids:
                raise NotFound()
            self._request({'request_type': 'switch', 'slot_id': mine.id,
                           'target_slot_id': int(target_shift_id or 0), 'reason': post.get('note') or False})
        except (UserError, ValidationError, ValueError) as error:
            return self._shift_page(error=str(error.args[0] if error.args else error), form=post)
        return self._shift_page(message=request.env._('Your swap is sent to your colleague.'))

    @http.route('/my/hr/shifts/unavailable', type='http', auth='user', website=True, methods=['POST'])
    def hr_shift_unavailable(self, **post):
        employee = self._employee()
        try:
            date_from = fields.Date.to_date(post.get('date_from'))
            date_to = fields.Date.to_date(post.get('date_to') or post.get('date_from'))
            if not date_from or date_to < date_from:
                raise ValidationError(request.env._('An unavailability ends after it starts.'))
            tz = ZoneInfo(employee.resource_id.tz or 'UTC')
            start = datetime.combine(date_from, time.min, tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
            stop = datetime.combine(date_to, time(23, 59, 59), tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
            with request.env.cr.savepoint():
                request.env['resource.calendar.leaves'].sudo().create({
                    'name': post.get('reason') or request.env._('Unavailable'),
                    'resource_id': employee.resource_id.id,
                    'company_id': employee.company_id.id,
                    'date_from': start,
                    'date_to': stop,
                    'shift_unavailability': True,
                })
        except (UserError, ValidationError, ValueError, TypeError) as error:
            return self._shift_page(error=str(error.args[0] if error.args else error), form=post)
        return request.redirect('/my/hr/shifts')

    @http.route('/my/hr/shifts/unavailable/<int:unavailability_id>/delete', type='http', auth='user', website=True,
                methods=['POST'])
    def hr_shift_unavailable_delete(self, unavailability_id, **post):
        leave = request.env['resource.calendar.leaves'].sudo().browse(unavailability_id).exists()
        if not leave or not leave.shift_unavailability or leave.resource_id != self._employee().resource_id:
            raise NotFound()
        leave.unlink()
        return request.redirect('/my/hr/shifts')

    @http.route('/my/hr/shifts/requests/<int:request_id>/<any(accept,decline):answer>', type='http', auth='user',
                website=True, methods=['POST'])
    def hr_shift_answer(self, request_id, answer, **post):
        """ The colleague asked for a swap accepts or declines it. """
        shift_request = self._own('om.planning.request', request_id, employee_field='target_employee_id')
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
