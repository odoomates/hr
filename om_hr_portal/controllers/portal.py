from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class HrPortal(CustomerPortal):
    """ The HR pages of the website for the employees: each page shows only what belongs to the employee of the
    user logged in, read as the super user and filtered on that employee. Nothing is reached by changing an id in
    the address. """

    def _prepare_portal_counter_values(self, counter):
        if counter == 'om_hr_employee_count':
            return 'hr.employee', [('user_id', '=', request.env.uid)], 'sudo'
        return super()._prepare_portal_counter_values(counter)

    @staticmethod
    def _employee():
        """ :return: the employee of the user logged in, as the super user; 404 for anyone else """
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.uid)], limit=1)
        if not employee:
            raise NotFound()
        return employee

    @classmethod
    def _own(cls, model, record_id, employee_field='employee_id'):
        """ :return: the record of that id when it belongs to the employee of the user, as the super user """
        employee = cls._employee()
        record = request.env[model].sudo().browse(int(record_id)).exists()
        if not record or record[employee_field] != employee:
            raise NotFound()
        return record

    def _values(self, page, **values):
        return {**self._prepare_portal_layout_values(), 'employee': self._employee(), 'page_name': page,
                **values}

    @http.route('/my/hr', type='http', auth='user', website=True)
    def hr_home(self, **kwargs):
        return request.render('om_hr_portal.portal_my_hr', self._values('hr'))

    @http.route('/my/hr/profile', type='http', auth='user', website=True)
    def hr_profile(self, **kwargs):
        return request.render('om_hr_portal.portal_my_hr_profile', self._values('hr_profile'))
