from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import HrPortal


class HrPortalPreboarding(HrPortal):

    def _preboarding(self):
        """ :return: the pre-boarding of the employee of the user, the running one first, as the super user """
        employee = self._employee()
        preboarding = request.env['hr.preboarding'].sudo().search(
            [('employee_id', '=', employee.id), ('state', '!=', 'cancelled')], order='id desc').sorted(
            lambda p: p.state != 'running')[:1]
        if not preboarding:
            raise NotFound()
        if preboarding.state == 'running':
            preboarding._refresh()
        return preboarding

    def _line(self, line_id):
        line = self._preboarding().line_ids.filtered(lambda line: line.id == line_id)
        if not line:
            raise NotFound()
        return line

    @staticmethod
    def _form_fields(line):
        """ :return: the inputs of the form of the step, filled with the last answer or the employee's values """
        model, names = line._fields_of_kind()
        values = dict(line._current_values(), **(line.data or {}))
        inputs = []
        for name in names:
            field = model._fields[name]
            item = {'name': name, 'label': field._description_string(request.env), 'type': field.type,
                    'value': values.get(name)}
            if field.type == 'selection':
                item['options'] = field._description_selection(request.env)
            elif field.type == 'many2one':
                item['options'] = [(record.id, record.display_name)
                                   for record in request.env[field.comodel_name].sudo().search([], order='name')]
            inputs.append(item)
        return inputs

    def _step_page(self, line, **values):
        return request.render('om_hr_preboarding.portal_my_welcome_step', self._values(
            'hr_welcome', line=line, preboarding=line.preboarding_id, inputs=self._form_fields(line),
            auto=line.kind in request.env['hr.preboarding.step']._auto_kinds(),
            om_section='Welcome', om_section_url='/my/welcome', om_record=line.name, **values))

    @http.route('/my/welcome', type='http', auth='user', website=True)
    def hr_welcome(self, **kwargs):
        return request.render('om_hr_preboarding.portal_my_welcome', self._values(
            'hr_welcome', preboarding=self._preboarding(), om_section='Welcome'))

    @http.route('/my/welcome/<int:line_id>', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def hr_welcome_step(self, line_id, **post):
        line = self._line(line_id)
        if request.httprequest.method != 'POST':
            return self._step_page(line)
        post.pop('csrf_token', None)
        try:
            line._submit(post)
        except UserError as error:
            return self._step_page(line, error=str(error), posted=post)
        return request.redirect('/my/welcome')
