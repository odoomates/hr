from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestAppraisalSurvey(TransactionCase):
    """ The 360 feedback: the manager asks reviewers, the employee reads the answers combined without the names,
    from three answers and once the appraisal is done. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_user = new_test_user(cls.env, 'om_360_employee', groups='base.group_user')
        cls.manager_user = new_test_user(cls.env, 'om_360_manager', groups='base.group_user')
        cls.peer_user = new_test_user(cls.env, 'om_360_peer', groups='base.group_user')
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': '360 Manager', 'user_id': cls.manager_user.id})
        cls.employee = Employee.create({'name': '360 Employee', 'user_id': cls.employee_user.id,
                                        'parent_id': cls.manager.id, 'work_email': 'employee@example.com'})
        cls.peers = Employee.create([{
            'name': '360 Peer %s' % index, 'parent_id': cls.manager.id, 'work_email': 'peer%s@example.com' % index,
        } for index in range(3)])
        cls.peers[0].user_id = cls.peer_user
        cls.survey = cls.env.ref('om_hr_appraisal_survey.survey_360')
        cls.appraisal = cls.env['hr.appraisal'].create({'employee_id': cls.employee.id})
        cls.appraisal.action_start()

    def _ask(self, reviewers, relation='peer'):
        wizard_form = Form(self.env['hr.appraisal.feedback.request'].with_user(self.manager_user).with_context(
            default_appraisal_id=self.appraisal.id))
        wizard_form.relation = relation
        wizard = wizard_form.save()
        wizard.reviewer_ids = self.env['hr.employee.public'].browse(reviewers.ids)
        wizard.action_send()

    def _answer(self, request, scale, text):
        answer = request.sudo().user_input_id
        Line = self.env['survey.user_input.line'].sudo()
        Line.create([{
            'user_input_id': answer.id, 'question_id': self.env.ref('om_hr_appraisal_survey.survey_360_quality').id,
            'answer_type': 'scale', 'value_scale': scale,
        }, {
            'user_input_id': answer.id, 'question_id': self.env.ref('om_hr_appraisal_survey.survey_360_keep').id,
            'answer_type': 'text_box', 'value_text_box': text,
        }])
        answer.state = 'done'

    def test_suggested_peers(self):
        wizard_form = Form(self.env['hr.appraisal.feedback.request'].with_user(self.manager_user).with_context(
            default_appraisal_id=self.appraisal.id))
        self.assertEqual(set(wizard_form.reviewer_ids.ids), set(self.peers.ids), 'The other reports of the manager')
        wizard_form.relation = 'manager'
        self.assertEqual(wizard_form.reviewer_ids.ids, self.manager.ids)

    def test_ask_answer_and_read(self):
        self._ask(self.peers)
        requests = self.env['hr.appraisal.feedback'].search([('appraisal_id', '=', self.appraisal.id)])
        self.assertEqual(len(requests), 3)
        self.assertEqual(set(requests.mapped('state')), {'sent'})
        self.assertEqual(requests.user_input_id.partner_id, self.peers.work_contact_id)
        invitations = self.env['mail.mail'].search([
            ('recipient_ids', 'in', self.peers.work_contact_id.ids), ('body_html', 'ilike', 'answer_token=')])
        self.assertEqual(len(invitations), 3, 'Each reviewer gets their own link')

        as_manager = self.appraisal.with_user(self.manager_user)
        as_employee = self.appraisal.with_user(self.employee_user)
        self._answer(requests[0], 5, 'Clear specs')
        self._answer(requests[1], 3, 'Helps everyone')
        self.assertEqual(as_manager.feedback_done_count, 2)
        self.assertIn('360 Peer 0', as_manager.feedback_detail, 'The manager reads who answered')
        self.assertIn('4.0 on average', as_manager.feedback_summary)
        self.assertFalse(as_employee.feedback_summary, 'Not before the appraisal is done')

        self._answer(requests[2], 4, 'Always on time')
        self.appraisal.write({'rating_id': self.env.ref('om_hr_appraisal.rating_meets').id})
        self.appraisal.sudo().state = 'review'
        self.appraisal.action_done()
        as_employee.invalidate_recordset()
        summary = as_employee.feedback_summary
        self.assertIn('4.0 on average, from 3 answers', summary)
        self.assertIn('Always on time', summary)
        self.assertNotIn('360 Peer', summary, 'The employee never reads the names')
        self.assertFalse(as_employee.feedback_detail)
        self.assertFalse(as_employee.feedback_count)
        with self.assertRaises(AccessError):
            requests.with_user(self.employee_user).read(['reviewer_id'])
        with self.assertRaises(AccessError):
            requests.with_user(self.peer_user).read(['reviewer_id'])

    def test_too_few_answers_for_the_employee(self):
        self._ask(self.peers[:2])
        for request, scale in zip(self.env['hr.appraisal.feedback'].search(
                [('appraisal_id', '=', self.appraisal.id)]), (2, 5), strict=True):
            self._answer(request, scale, 'Fine')
        self.appraisal.sudo().write({'state': 'done', 'rating_id': self.env.ref('om_hr_appraisal.rating_meets').id})
        summary = self.appraisal.with_user(self.employee_user).feedback_summary
        self.assertIn('once 3 people answered', summary)
        self.assertNotIn('Fine', summary)

    def test_only_manager_and_hr_ask(self):
        with self.assertRaises(UserError):
            self.appraisal.with_user(self.employee_user).action_request_feedback()
        with self.assertRaises(UserError):
            self._ask(self.employee)
        no_email = self.env['hr.employee'].create({'name': '360 No Email', 'parent_id': self.manager.id})
        with self.assertRaises(UserError):
            self._ask(no_email)
