from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import OmHrPortal


class OmHrPortalLeave(OmHrPortal):

    def _om_leave_types(self, employee):
        return request.env['hr.work.entry.type'].sudo().search([
            ('time_off_selectable', '=', True),
            '|', ('country_id', '=', False), ('country_id', '=', employee.company_id.country_id.id)])

    def _om_balances(self, employee):
        """ :return: per time type needing an allocation, what is left and what was given, as in the backend """
        types = self._om_leave_types(employee).filtered('requires_allocation')
        data = types.with_company(employee.company_id).get_allocation_data(employee)[employee] if types else []
        return [{'name': name, 'left': info['virtual_remaining_leaves'], 'total': info['max_leaves'],
                 'unit': info['unit_of_measure']} for name, info, _requires, _id in data if info['max_leaves']]

    def _om_leave_page(self, error=None, values=None):
        employee = self._om_employee()
        leaves = request.env['hr.leave'].sudo().search([('employee_id', '=', employee.id)],
                                                        order='request_date_from desc', limit=50)
        return request.render('om_hr_portal_leave.portal_my_time_off', self._om_values(
            'om_hr_time_off', leaves=leaves, balances=self._om_balances(employee),
            leave_types=self._om_leave_types(employee), error=error, form=values or {}, om_section='Time Off'))

    @http.route('/my/hr/time-off', type='http', auth='user', website=True)
    def om_hr_time_off(self, **kwargs):
        return self._om_leave_page()

    @http.route('/my/hr/time-off/new', type='http', auth='user', website=True, methods=['POST'])
    def om_hr_time_off_new(self, **post):
        employee = self._om_employee()
        try:
            leave_type = self._om_leave_types(employee).browse(int(post.get('work_entry_type_id') or 0))
            if leave_type not in self._om_leave_types(employee):
                raise UserError(request.env._('Choose a type of time off.'))
            date_from = fields.Date.to_date(post.get('date_from'))
            date_to = fields.Date.to_date(post.get('date_to') or post.get('date_from'))
            if not date_from or not date_to or date_to < date_from:
                raise UserError(request.env._('Give the first and the last day of the time off.'))
            with request.env.cr.savepoint():
                request.env['hr.leave'].sudo().create({
                    'employee_id': employee.id,
                    'work_entry_type_id': leave_type.id,
                    'request_date_from': date_from,
                    'request_date_to': date_to,
                    'name': post.get('name') or False,
                })
        except (UserError, ValidationError, ValueError) as error:
            return self._om_leave_page(error=str(error.args[0] if error.args else error), values=post)
        return request.redirect('/my/hr/time-off')

    @http.route('/my/hr/time-off/<int:leave_id>/cancel', type='http', auth='user', website=True, methods=['POST'])
    def om_hr_time_off_cancel(self, leave_id, **post):
        """ A request not approved yet is withdrawn; an approved one is cancelled by HR. """
        leave = self._om_own('hr.leave', leave_id)
        if leave.state == 'confirm':
            leave.unlink()
        return request.redirect('/my/hr/time-off')
