from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import HrPortal


class HrPortalExit(HrPortal):

    def _exit_page(self, error=None, form=None):
        employee = self._employee()
        exits = request.env['hr.exit'].sudo().search([('employee_id', '=', employee.id)])
        return request.render('om_hr_portal_exit.portal_my_exit', self._values(
            'om_hr_exit', exits=exits, error=error, form=form or {}, om_section='Resignation',
            open_exit=exits.filtered(lambda e: e.state in ('draft', 'to_approve', 'approved'))[:1]))

    @http.route('/my/hr/resignation', type='http', auth='user', website=True)
    def hr_exit(self, **kwargs):
        return self._exit_page()

    @http.route('/my/hr/resignation/new', type='http', auth='user', website=True, methods=['POST'])
    def hr_exit_new(self, **post):
        employee = self._employee()
        try:
            if not post.get('confirm'):
                raise UserError(request.env._('Tick the box to confirm your resignation.'))
            values = {'employee_id': employee.id, 'note': post.get('note') or False}
            if post.get('date_notice'):
                values['date_notice'] = fields.Date.to_date(post['date_notice'])
            with request.env.cr.savepoint():
                exit_ = request.env['hr.exit'].sudo().create(values)
                exit_.action_submit()
        except (UserError, ValidationError, ValueError) as error:
            return self._exit_page(error=str(error.args[0] if error.args else error), form=post)
        return request.redirect('/my/hr/resignation')
