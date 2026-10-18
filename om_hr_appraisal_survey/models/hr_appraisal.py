from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError

# the employee reads the combined answers from this many answers on, so that no answer points to its author
MIN_ANSWERS = 3


class HrAppraisal(models.Model):
    _inherit = 'hr.appraisal'

    feedback_ids = fields.One2many('hr.appraisal.feedback', 'appraisal_id', string='360 Feedback',
                                   groups='hr.group_hr_user')
    feedback_count = fields.Integer(compute='_compute_feedback_360')
    feedback_done_count = fields.Integer(compute='_compute_feedback_360')
    feedback_summary = fields.Html(
        string='360 Feedback Summary', compute='_compute_feedback_360', sanitize=False,
        help='The answers of everyone combined, without the names.')
    feedback_detail = fields.Html(
        string='360 Feedback Answers', compute='_compute_feedback_360', sanitize=False,
        help='Who answered what: for the manager and HR only.')

    def _feedback_requests(self):
        """ The requests of the appraisal, read as the super user: the manager is not an HR officer. """
        self.ensure_one()
        return self.env['hr.appraisal.feedback'].sudo().search([('appraisal_id', '=', self.id)])

    @api.depends('state', 'employee_id', 'manager_id')
    @api.depends_context('uid')
    def _compute_feedback_360(self):
        for appraisal in self:
            requests = appraisal._feedback_requests() if appraisal.id else self.env['hr.appraisal.feedback']
            answered = requests.filtered(lambda request: request.user_input_id.state == 'done')
            roles = appraisal._roles()
            reviewer = bool(roles & {'hr', 'manager'})
            appraisal.feedback_count = len(requests) if reviewer else 0
            appraisal.feedback_done_count = len(answered)
            appraisal.feedback_detail = appraisal._render_feedback_detail(answered) if reviewer else False
            if reviewer or ('employee' in roles and appraisal.state == 'done'):
                appraisal.feedback_summary = appraisal._render_feedback_summary(answered, reviewer)
            else:
                appraisal.feedback_summary = False

    @staticmethod
    def _answer_value(line):
        if line.answer_type == 'suggestion':
            return line.suggested_answer_id.value
        if line.answer_type in ('scale', 'numerical_box'):
            return line.value_scale if line.answer_type == 'scale' else line.value_numerical_box
        return line['value_%s' % line.answer_type] if line.answer_type else ''

    def _answered_questions(self, answers):
        lines = answers.user_input_line_ids.filtered(lambda line: not line.skipped)
        return lines.question_id.sorted(lambda question: (question.sequence, question.id)), lines

    def _render_feedback_summary(self, answered, reviewer):
        """ :return: the answers combined per question: the average of the scales, the count of each choice, and
            the texts sorted, without the names; for the employee only from MIN_ANSWERS answers """
        if len(answered) < MIN_ANSWERS and not reviewer:
            return Markup('<p class="text-muted">%s</p>') % self.env._(
                'The answers show here once %s people answered.', MIN_ANSWERS)
        if not answered:
            return Markup('<p class="text-muted">%s</p>') % self.env._('No answer yet.')
        questions, lines = self._answered_questions(answered.user_input_id)
        parts = []
        for question in questions:
            question_lines = lines.filtered(lambda line, question=question: line.question_id == question)
            if question.question_type in ('scale', 'numerical_box'):
                values = [self._answer_value(line) for line in question_lines]
                text = self.env._('%(average).1f on average, from %(count)s answers',
                                  average=sum(values) / len(values), count=len(values))
                if question.question_type == 'scale':
                    text += ' (%s-%s)' % (question.scale_min, question.scale_max)
                body = Markup('<p>%s</p>') % text
            elif question.question_type in ('simple_choice', 'multiple_choice'):
                counts = {}
                for line in question_lines:
                    counts[line.suggested_answer_id.value] = counts.get(line.suggested_answer_id.value, 0) + 1
                body = Markup('<ul>%s</ul>') % Markup().join(
                    Markup('<li>%s: %s</li>') % (value, count) for value, count in sorted(counts.items()))
            else:
                # sorted, not in the order of the answers, which would follow the order of the reviewers
                texts = sorted(str(self._answer_value(line)) for line in question_lines)
                body = Markup('<ul>%s</ul>') % Markup().join(Markup('<li>%s</li>') % text for text in texts)
            parts.append(Markup('<h5>%s</h5>%s') % (question.title, body))
        return Markup().join(parts)

    def _render_feedback_detail(self, answered):
        """ :return: who answered what, for the manager and HR """
        if not answered:
            return False
        relations = dict(self.env['hr.appraisal.feedback']._fields['relation']._description_selection(self.env))
        parts = []
        for request in answered:
            questions, lines = self._answered_questions(request.user_input_id)
            rows = Markup().join(
                Markup('<li><strong>%s</strong>: %s</li>') % (
                    question.title, ', '.join(str(self._answer_value(line)) for line in lines
                                              if line.question_id == question))
                for question in questions)
            parts.append(Markup('<h5>%s (%s)</h5><ul>%s</ul>') % (
                request.reviewer_id.name, relations.get(request.relation), rows))
        return Markup().join(parts)

    def action_request_feedback(self):
        self.ensure_one()
        if not self._roles() & {'hr', 'manager'}:
            raise UserError(self.env._('The manager and HR ask for the 360 feedback of %s.', self.name))
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Ask for 360 Feedback'),
            'res_model': 'hr.appraisal.feedback.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_appraisal_id': self.id},
        }

    def action_open_feedback(self):
        """ The requests of the appraisal and their status, for the manager and HR. """
        self.ensure_one()
        if not self._roles() & {'hr', 'manager'}:
            raise UserError(self.env._('The manager and HR follow the 360 feedback of %s.', self.name))
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('360 Feedback'),
            'res_model': 'hr.appraisal.feedback',
            'view_mode': 'list',
            'domain': [('appraisal_id', '=', self.id)],
            'context': {'create': False},
        }
