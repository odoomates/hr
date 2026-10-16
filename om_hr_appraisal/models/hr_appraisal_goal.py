from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class OmHrAppraisalGoal(models.Model):
    """ What an employee aims at until the next appraisal; they update its progress themselves. """
    _name = 'om.hr.appraisal.goal'
    _inherit = ['mail.thread']
    _description = 'Appraisal Goal'
    _order = 'date_deadline, id'

    name = fields.Char(string='Goal', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, index=True, tracking=True)
    manager_id = fields.Many2one(related='employee_id.parent_id', string='Manager')
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    appraisal_id = fields.Many2one('om.hr.appraisal', string='Appraisal', index=True, ondelete='set null')
    description = fields.Html()
    target = fields.Char(help='How to tell the goal is reached, e.g. Close 20 deals a quarter.')
    date_deadline = fields.Date(string='Due Date', tracking=True)
    progress = fields.Integer(default=0, tracking=True, help='How far the goal is reached, in percent.')
    is_done = fields.Boolean(string='Reached', compute='_compute_is_done', store=True)

    _progress_range = models.Constraint('CHECK(progress BETWEEN 0 AND 100)',
                                        'The progress of a goal is between 0 and 100 percent.')

    @api.depends('progress')
    def _compute_is_done(self):
        for goal in self:
            goal.is_done = goal.progress >= 100

    def write(self, vals):
        # an employee only updates how far their own goals are reached
        if not self.env.su and not self.env.user.has_group('hr.group_hr_user') and set(vals) - {'progress'}:
            if any(goal.employee_id.parent_id.user_id != self.env.user for goal in self):
                raise AccessError(_('You update the progress of your goals; your manager sets them.'))
        return super().write(vals)
