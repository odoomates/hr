from odoo import http
from odoo.http import request

from ..models.hr_pulse import hash_token


class PulseSurvey(http.Controller):

    @http.route('/pulse/<string:token>', type='http', auth='public', website=False, sitemap=False)
    def pulse_answer(self, token, **kwargs):
        """ The one-time link of an employee: the survey answer of their ballot, which does not know them. """
        ballot = request.env['hr.pulse.ballot'].sudo().search([('token_hash', '=', hash_token(token))], limit=1)
        if not ballot or ballot.pulse_id.state != 'running':
            return request.render('om_hr_survey.pulse_closed')
        answer = ballot._get_answer()
        if answer.state == 'done':
            return request.render('om_hr_survey.pulse_closed', {'answered': True})
        return request.redirect('%s?answer_token=%s' % (answer.survey_id.get_start_url(), answer.access_token))
