import re
from datetime import date, timedelta

from freezegun import freeze_time

from odoo.exceptions import AccessError
from odoo.tests import HttpCase, new_test_user, tagged

from odoo.addons.om_hr_survey.models.hr_pulse import hash_token


@tagged('post_install', '-at_install')
class TestPulse(HttpCase):
    """ Anonymous pulse surveys: one-time links, ballots that know a department only, results from five answers. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_user = new_test_user(cls.env, 'om_pulse_hr', groups='base.group_user,hr.group_hr_user')
        cls.employee_user = new_test_user(cls.env, 'om_pulse_employee', groups='base.group_user')
        cls.sales = cls.env['hr.department'].create({'name': 'Pulse Sales'})
        cls.support = cls.env['hr.department'].create({'name': 'Pulse Support'})
        Employee = cls.env['hr.employee']
        cls.employees = Employee.create([{
            'name': 'Pulse Sales %s' % index, 'department_id': cls.sales.id,
            'work_email': 'pulse.sales%s@example.com' % index} for index in range(6)])
        cls.employees |= Employee.create([{
            'name': 'Pulse Support %s' % index, 'department_id': cls.support.id,
            'work_email': 'pulse.support%s@example.com' % index} for index in range(2)])
        Employee.create({'name': 'Pulse No Email', 'department_id': cls.sales.id})
        cls.pulse = cls.env['hr.pulse'].with_user(cls.hr_user).create({
            'name': 'Pulse Test', 'department_ids': [(4, cls.sales.id), (4, cls.support.id)],
            'date_start': date.today(), 'date_end': date.today() + timedelta(days=7), 'repeat_weeks': 4})

    def _links(self):
        mails = self.env['mail.mail'].search([('body_html', 'ilike', '/pulse/')])
        return {mail.email_to: re.search(r'/pulse/([\w-]+)', mail.body_html).group(1) for mail in mails}

    def _answer(self, token, score, text=None):
        ballot = self.env['hr.pulse.ballot'].sudo().search([('token_hash', '=', hash_token(token))])
        answer = ballot._get_answer()
        Line = self.env['survey.user_input.line'].sudo()
        Line.create({'user_input_id': answer.id, 'question_id': self.env.ref('om_hr_survey.survey_pulse_enps').id,
                     'answer_type': 'scale', 'value_scale': score})
        if text:
            Line.create({'user_input_id': answer.id,
                         'question_id': self.env.ref('om_hr_survey.survey_pulse_comment').id,
                         'answer_type': 'text_box', 'value_text_box': text})
        answer.state = 'done'

    def test_anonymous_ballots(self):
        self.pulse.action_launch()
        self.assertEqual(self.pulse.state, 'running')
        self.assertEqual(self.pulse.invitation_ids.employee_id, self.employees, 'Those with a work email')
        ballots = self.env['hr.pulse.ballot'].sudo().search([('pulse_id', '=', self.pulse.id)])
        self.assertEqual(len(ballots), 8)
        self.assertFalse({'employee_id', 'partner_id', 'user_id'} & set(ballots._fields),
                         'A ballot never knows the employee')
        links = self._links()
        self.assertEqual(len(links), 8, 'One link each')
        self.assertFalse(ballots.filtered(lambda ballot: ballot.token_hash in links.values()),
                         'Only the hash of a link is stored')
        with self.assertRaises(AccessError):
            ballots.with_user(self.hr_user).read(['department_id'])

        # the link opens the survey, the same answer until it is done, then a thank you
        token = links['pulse.sales0@example.com']
        response = self.url_open('/pulse/%s' % token, allow_redirects=False)
        self.assertIn('/survey/start/', response.headers['Location'])
        ballot = ballots.filtered(lambda ballot: ballot.token_hash == hash_token(token))
        self.assertFalse(ballot.user_input_id.partner_id)
        self.assertEqual(self.url_open('/pulse/%s' % token, allow_redirects=False).headers['Location'],
                         response.headers['Location'])
        self._answer(token, 10)
        self.assertIn('Thank you', self.url_open('/pulse/%s' % token).text)
        self.assertIn('not valid', self.url_open('/pulse/not-a-link').text)

    def test_results_from_five_answers(self):
        self.pulse.action_launch()
        links = self._links()
        scores = {'pulse.sales%s@example.com' % index: score for index, score in enumerate((10, 9, 8, 6, 3))}
        for email, score in scores.items():
            self._answer(links[email], score, 'Sales comment %s' % score)
        self._answer(links['pulse.support0@example.com'], 0, 'Support comment')
        results = self.pulse.with_user(self.hr_user).results
        self.assertIn('Pulse Sales', results)
        self.assertIn('eNPS: 0', results, 'Two promoters, two detractors in five')
        self.assertIn('Sales comment 3', results)
        self.assertNotIn('Support comment', results, 'One answer in Support: left out, of Everyone too')
        self.assertNotIn('Pulse Support', results)
        self.assertIn('1 answers of smaller groups are left out', results)

        self.pulse.action_close()
        self.assertEqual(self.pulse.answer_count, 6)
        self.assertEqual(self.pulse.participation, 75.0)
        self.assertEqual(self.pulse.enps, 0.0, 'Of the answers shown: the one of Support is left out')
        following = self.env['hr.pulse'].search([('name', '=', 'Pulse Test'), ('state', '=', 'draft')])
        self.assertEqual(following.date_start, date.today() + timedelta(weeks=4))
        with freeze_time(date.today() + timedelta(weeks=4)):
            self.env['hr.pulse']._cron_pulse()
        self.assertEqual(following.state, 'running', 'Launched on its start date')
