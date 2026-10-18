from odoo import api, fields, models


class HrAppraisalFeedback(models.Model):
    """ A person asked to answer the 360 survey about the employee of an appraisal. Only the manager and HR read
    who was asked and what they answered; the employee reads the answers combined, on the appraisal. """
    _name = 'hr.appraisal.feedback'
    _description = '360 Feedback Request'
    _check_company_auto = True
    _order = 'id'

    appraisal_id = fields.Many2one('hr.appraisal', required=True, index=True, ondelete='cascade',
                                   check_company=True)
    company_id = fields.Many2one(related='appraisal_id.company_id', store=True, index=True)
    reviewer_id = fields.Many2one('hr.employee', required=True)
    relation = fields.Selection([
        ('manager', 'Manager'),
        ('peer', 'Peer'),
        ('report', 'Direct Report'),
        ('other', 'Other'),
    ], required=True, default='peer')
    survey_id = fields.Many2one('survey.survey', required=True)
    user_input_id = fields.Many2one('survey.user_input', string='Answer', ondelete='set null', copy=False)
    date_deadline = fields.Date(string='Deadline')
    state = fields.Selection([
        ('sent', 'Sent'),
        ('in_progress', 'In Progress'),
        ('done', 'Answered'),
    ], compute='_compute_state')

    @api.depends('user_input_id.state')
    def _compute_state(self):
        for request in self:
            state = request.sudo().user_input_id.state
            request.state = 'done' if state == 'done' else 'in_progress' if state == 'in_progress' else 'sent'
