import hashlib
import random
import secrets
from datetime import timedelta

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError

# the results of a group show from this many answers on, so that no answer points to its author
MIN_ANSWERS = 5


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


class HrPulse(models.Model):
    """ An anonymous pulse survey of the employees.

    Each employee invited gets a one-time link by email. The link opens a ballot that knows the department of the
    employee but not the employee: the invitations hold who was asked, the ballots hold the answers, and nothing
    links one to the other. The ballots are created in a random order, and only the hash of the link is stored.
    """
    _name = 'hr.pulse'
    _inherit = ['mail.thread']
    _description = 'Pulse Survey'
    _check_company_auto = True
    _order = 'date_start desc, id desc'

    name = fields.Char(required=True, tracking=True)
    survey_id = fields.Many2one(
        'survey.survey', required=True, domain=[('survey_type', '=', 'survey')],
        default=lambda self: self.env.ref('om_hr_survey.survey_pulse', raise_if_not_found=False))
    enps_question_id = fields.Many2one(
        'survey.question', string='eNPS Question', domain="[('survey_id', '=', survey_id), ('question_type', '=', "
                                                          "'scale')]",
        compute='_compute_enps_question_id', store=True, readonly=False,
        help='The question from 0 to 10 the eNPS is computed on: the share of promoters (9 and 10) less the share '
             'of detractors (0 to 6).')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    department_ids = fields.Many2many('hr.department', string='Departments', check_company=True,
                                      help='Leave empty to ask all the employees of the company.')
    date_start = fields.Date(string='Start', required=True, default=fields.Date.context_today)
    date_end = fields.Date(string='Answer By', required=True,
                           default=lambda self: fields.Date.context_today(self) + timedelta(days=7))
    repeat_weeks = fields.Integer(
        string='Repeat Every', default=0,
        help='Weeks between two pulses: the next one is launched when this one closes. 0 launches none.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('closed', 'Closed'),
    ], required=True, default='draft', copy=False, tracking=True)
    invitation_ids = fields.One2many('hr.pulse.invitation', 'pulse_id', string='Invited')
    invited_count = fields.Integer(compute='_compute_counts')
    answer_count = fields.Integer(string='Answers', compute='_compute_counts')
    # kept when the pulse closes, for the trend of the pulses
    participation = fields.Float(compute='_compute_final', store=True, aggregator='avg',
                                 help='The share of the employees asked who answered, once closed.')
    enps = fields.Float(string='eNPS', compute='_compute_final', store=True, aggregator='avg', digits=(16, 0),
                        help='From -100, all detractors, to 100, all promoters, once closed; 0 under five answers.')
    results = fields.Html(compute='_compute_results', sanitize=False)

    @api.depends('survey_id')
    def _compute_enps_question_id(self):
        for pulse in self:
            pulse.enps_question_id = pulse.survey_id.question_ids.filtered(
                lambda question: question.question_type == 'scale' and question.scale_min == 0
                and question.scale_max == 10)[:1]

    def _ballots(self, department=None):
        """ The ballots answered, read as the super user: no user reads a ballot on its own. """
        self.ensure_one()
        domain = [('pulse_id', '=', self.id), ('user_input_id.state', '=', 'done')]
        if department is not None:
            domain.append(('department_id', '=', department.id))
        return self.env['hr.pulse.ballot'].sudo().search(domain)

    def _enps(self, ballots):
        """ :return: the eNPS of the ballots, or None under MIN_ANSWERS answers """
        if len(ballots) < MIN_ANSWERS or not self.enps_question_id:
            return None
        lines = ballots.user_input_id.user_input_line_ids.filtered(
            lambda line: line.question_id == self.enps_question_id and not line.skipped)
        if not lines:
            return None
        scores = lines.mapped('value_scale')
        promoters = len([score for score in scores if score >= 9])
        detractors = len([score for score in scores if score <= 6])
        return round(100.0 * (promoters - detractors) / len(scores))

    @api.depends('invitation_ids')
    def _compute_counts(self):
        for pulse in self:
            pulse.invited_count = len(pulse.invitation_ids)
            pulse.answer_count = len(pulse._ballots()) if pulse.id else 0

    @api.depends('state')
    def _compute_final(self):
        for pulse in self:
            if pulse.state != 'closed':
                pulse.participation = pulse.enps = 0.0
                continue
            ballots = pulse._ballots()
            pulse.participation = 100.0 * len(ballots) / len(pulse.invitation_ids) if pulse.invitation_ids else 0.0
            enps = pulse._enps(pulse._shown_ballots())
            pulse.enps = enps if enps is not None else 0.0

    def _render_group(self, title, ballots):
        """ The results of a group of ballots: the eNPS, the average of each scale, the texts sorted. """
        if len(ballots) < MIN_ANSWERS:
            return Markup('<h4>%s</h4><p class="text-muted">%s</p>') % (title, self.env._(
                '%(count)s answers: the results show from %(min)s answers.', count=len(ballots), min=MIN_ANSWERS))
        parts = [Markup('<h4>%s</h4>') % title]
        enps = self._enps(ballots)
        if enps is not None:
            parts.append(Markup('<p><strong>eNPS: %s</strong> (%s)</p>') % (
                enps, self.env._('%s answers', len(ballots))))
        lines = ballots.user_input_id.user_input_line_ids.filtered(lambda line: not line.skipped)
        for question in lines.question_id.sorted(lambda question: (question.sequence, question.id)):
            if question == self.enps_question_id:
                continue
            question_lines = lines.filtered(lambda line, question=question: line.question_id == question)
            if question.question_type in ('scale', 'numerical_box'):
                values = question_lines.mapped('value_scale' if question.question_type == 'scale'
                                               else 'value_numerical_box')
                body = Markup('<p>%s</p>') % self.env._('%(average).1f on average', average=sum(values) / len(values))
            elif question.question_type in ('simple_choice', 'multiple_choice'):
                counts = {}
                for line in question_lines:
                    counts[line.suggested_answer_id.value] = counts.get(line.suggested_answer_id.value, 0) + 1
                body = Markup('<ul>%s</ul>') % Markup().join(
                    Markup('<li>%s: %s</li>') % item for item in sorted(counts.items()))
            else:
                texts = sorted(str(line['value_%s' % line.answer_type]) for line in question_lines)
                body = Markup('<ul>%s</ul>') % Markup().join(Markup('<li>%s</li>') % text for text in texts)
            parts.append(Markup('<h5>%s</h5>%s') % (question.title, body))
        return Markup().join(parts)

    def _groups(self):
        """ :return: the groups of ballots shown, as (title, ballots), and the count of ballots left out.

        A department shows from MIN_ANSWERS answers. The smaller ones are pooled, and shown together from
        MIN_ANSWERS answers; else they are left out of every result, Everyone included: comparing Everyone with
        the departments shown would otherwise tell what they answered.
        """
        self.ensure_one()
        ballots = self._ballots()
        groups, small = [], self.env['hr.pulse.ballot']
        for department in ballots.department_id.sorted('name'):
            group = ballots.filtered(lambda ballot, department=department: ballot.department_id == department)
            if len(group) >= MIN_ANSWERS:
                groups.append((department.name, group))
            else:
                small |= group
        small |= ballots.filtered(lambda ballot: not ballot.department_id)
        if len(small) >= MIN_ANSWERS:
            groups.append((self.env._('Other Departments'), small))
            small = self.env['hr.pulse.ballot']
        return groups, len(small)

    def _shown_ballots(self):
        groups, _left_out = self._groups()
        return self.env['hr.pulse.ballot'].sudo().union(*(ballots for _title, ballots in groups))

    @api.depends('state', 'invitation_ids')
    def _compute_results(self):
        for pulse in self:
            if not pulse.id or pulse.state == 'draft':
                pulse.results = False
                continue
            groups, left_out = pulse._groups()
            shown = self.env['hr.pulse.ballot'].sudo().union(*(ballots for _title, ballots in groups))
            parts = [pulse._render_group(self.env._('Everyone'), shown)]
            parts += [pulse._render_group(title, ballots) for title, ballots in groups]
            if left_out:
                parts.append(Markup('<p class="text-muted">%s</p>') % self.env._(
                    '%(count)s answers of smaller groups are left out, to keep them anonymous: a group shows from '
                    '%(min)s answers.', count=left_out, min=MIN_ANSWERS))
            pulse.results = Markup().join(parts)

    def _get_employees(self):
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id)]
        if self.department_ids:
            domain.append(('department_id', 'child_of', self.department_ids.ids))
        return self.env['hr.employee'].search(domain).filtered('work_email')

    def action_launch(self):
        """ A ballot per employee, created in a random order, and their one-time link by email. """
        template = self.env.ref('om_hr_survey.mail_template_pulse_invite')
        base_url = self.get_base_url()
        for pulse in self:
            if pulse.state != 'draft':
                raise UserError(self.env._('%s is already launched.', pulse.name))
            employees = pulse._get_employees()
            if not employees:
                raise UserError(self.env._('No employee with a work email to ask in %s.', pulse.name))
            links = {employee: secrets.token_urlsafe(24) for employee in employees}
            ballots = [{'pulse_id': pulse.id, 'token_hash': hash_token(token),
                        'department_id': employee.department_id.id} for employee, token in links.items()]
            random.shuffle(ballots)
            self.env['hr.pulse.ballot'].sudo().create(ballots)
            self.env['hr.pulse.invitation'].create([
                {'pulse_id': pulse.id, 'employee_id': employee.id} for employee in employees])
            pulse.state = 'running'
            for employee, token in links.items():
                template.with_context(pulse_url='%s/pulse/%s' % (base_url, token)).send_mail(
                    pulse.id, email_values={'email_to': employee.work_email, 'recipient_ids': [],
                                            'model': False, 'res_id': False})
        return True

    def action_close(self):
        for pulse in self.filtered(lambda pulse: pulse.state == 'running'):
            pulse.state = 'closed'
            if pulse.repeat_weeks > 0:
                shift = timedelta(weeks=pulse.repeat_weeks)
                pulse.copy({
                    'name': pulse.name,
                    'date_start': pulse.date_start + shift,
                    'date_end': pulse.date_end + shift,
                })
        return True

    @api.model
    def _cron_pulse(self):
        today = fields.Date.context_today(self)
        self.search([('state', '=', 'running'), ('date_end', '<', today)]).action_close()
        for pulse in self.search([('state', '=', 'draft'), ('repeat_weeks', '>', 0), ('date_start', '<=', today)]):
            pulse.action_launch()


class HrPulseInvitation(models.Model):
    """ Who was asked: never whether nor what they answered. """
    _name = 'hr.pulse.invitation'
    _description = 'Pulse Survey Invitation'

    pulse_id = fields.Many2one('hr.pulse', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='pulse_id.company_id', store=True)
    employee_id = fields.Many2one('hr.employee', required=True)
    department_id = fields.Many2one(related='employee_id.department_id')


class HrPulseBallot(models.Model):
    """ An answer to a pulse: the department of the employee, never the employee. Only the hash of their link is
    stored, and no user reads the ballots: the results are computed from them as the super user. """
    _name = 'hr.pulse.ballot'
    _description = 'Pulse Survey Ballot'

    pulse_id = fields.Many2one('hr.pulse', required=True, index=True, ondelete='cascade')
    token_hash = fields.Char(required=True, index=True)
    department_id = fields.Many2one('hr.department')
    user_input_id = fields.Many2one('survey.user_input', ondelete='set null')

    _token_uniq = models.Constraint('unique(token_hash)', 'A link opens one ballot.')

    def _get_answer(self):
        """ :return: the survey answer of the ballot, started the first time the link opens """
        self.ensure_one()
        if not self.user_input_id:
            self.user_input_id = self.pulse_id.survey_id._create_answer(
                check_attempts=False, deadline=fields.Datetime.to_datetime(self.pulse_id.date_end))
        return self.user_input_id
