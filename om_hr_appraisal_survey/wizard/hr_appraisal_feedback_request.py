from odoo import api, fields, models
from odoo.exceptions import UserError


class HrAppraisalFeedbackRequest(models.TransientModel):
    """ Sends the 360 survey of an appraisal to the people chosen, each with their own link. """
    _name = 'hr.appraisal.feedback.request'
    _description = 'Ask for 360 Feedback'

    appraisal_id = fields.Many2one('hr.appraisal', required=True, readonly=True)
    survey_id = fields.Many2one(
        'survey.survey', required=True, domain=[('survey_type', '=', 'survey')],
        default=lambda self: self.env.ref('om_hr_appraisal_survey.survey_360', raise_if_not_found=False))
    # the public employees: a manager who is not an HR officer reads them
    reviewer_ids = fields.Many2many('hr.employee.public', string='Reviewers', required=True)
    relation = fields.Selection(
        lambda self: self.env['hr.appraisal.feedback']._fields['relation'].selection,
        required=True, default='peer', help='How the reviewers work with the employee, shown to the manager.')
    date_deadline = fields.Date(string='Answer By')

    @api.onchange('appraisal_id', 'relation')
    def _onchange_relation(self):
        # the usual reviewers of each relation, to adjust
        employee = self.env['hr.employee.public'].browse(self.appraisal_id.employee_id.id)
        if not employee:
            return
        if self.relation == 'manager':
            self.reviewer_ids = employee.parent_id
        elif self.relation == 'report':
            self.reviewer_ids = employee.child_ids
        elif self.relation == 'peer' and employee.parent_id:
            self.reviewer_ids = employee.parent_id.child_ids - employee

    def action_send(self):
        self.ensure_one()
        appraisal = self.appraisal_id
        if not appraisal._roles() & {'hr', 'manager'}:
            raise UserError(self.env._('The manager and HR ask for the 360 feedback of %s.', appraisal.name))
        if appraisal.employee_id.id in self.reviewer_ids.ids:
            raise UserError(self.env._('%s does not review themselves here: that is the self assessment.',
                                       appraisal.employee_id.name))
        reviewers = self.env['hr.employee'].sudo().browse(self.reviewer_ids.ids)
        missing = reviewers.filtered(lambda reviewer: not reviewer.work_contact_id.email)
        if missing:
            raise UserError(self.env._('Set the work email of %s first: the survey is sent there.',
                                       ', '.join(missing.mapped('name'))))
        survey = self.survey_id.sudo()
        template = self.env.ref('survey.mail_template_user_input_invite', raise_if_not_found=False)
        invite = self.env['survey.invite'].sudo().create({
            'survey_id': survey.id,
            'template_id': template.id if template else False,
            'partner_ids': [fields.Command.set(reviewers.work_contact_id.ids)],
            'deadline': self.date_deadline,
        })
        for reviewer in reviewers:
            answer = survey._create_answer(partner=reviewer.work_contact_id, check_attempts=False,
                                           deadline=self.date_deadline)
            self.env['hr.appraisal.feedback'].sudo().create({
                'appraisal_id': appraisal.id,
                'reviewer_id': reviewer.id,
                'relation': self.relation,
                'survey_id': survey.id,
                'user_input_id': answer.id,
                'date_deadline': self.date_deadline,
            })
            invite._send_mail(answer)
        appraisal.message_post(body=self.env._('360 feedback asked from %s people.', len(reviewers)),
                               subtype_xmlid='mail.mt_note')
        return {'type': 'ir.actions.act_window_close'}
