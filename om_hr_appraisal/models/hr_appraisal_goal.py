from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class HrAppraisalGoal(models.Model):
    """ What an employee, a department or the company aims at. Employees update the progress of their own goals; a
    goal served by other goals takes the average of their progress, so the goals of the employees move the goals
    of their department and of the company. """
    _name = 'hr.appraisal.goal'
    _inherit = ['mail.thread']
    _description = 'Appraisal Goal'
    _check_company_auto = True
    _order = 'date_deadline, id'
    _parent_store = True

    name = fields.Char(string='Goal', required=True, tracking=True)
    level = fields.Selection([
        ('company', 'Company'),
        ('department', 'Department'),
        ('employee', 'Employee'),
    ], required=True, default='employee', tracking=True)
    employee_id = fields.Many2one('hr.employee', index=True, tracking=True, check_company=True)
    manager_id = fields.Many2one(related='employee_id.parent_id', string='Manager')
    department_id = fields.Many2one(
        'hr.department', index=True, tracking=True, check_company=True,
        compute='_compute_department_id', store=True, readonly=False, precompute=True)
    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        compute='_compute_company_id', store=True, readonly=False, precompute=True)
    appraisal_id = fields.Many2one('hr.appraisal', index=True, ondelete='set null', check_company=True)
    parent_id = fields.Many2one(
        'hr.appraisal.goal', string='Serves', index=True, ondelete='set null', check_company=True, tracking=True,
        help='The goal of the department or of the company this goal helps reach.')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('hr.appraisal.goal', 'parent_id', string='Served By')
    description = fields.Html()
    target = fields.Char(help='How to tell the goal is reached, e.g. Close 20 deals a quarter.')
    date_deadline = fields.Date(string='Due Date', tracking=True)
    progress = fields.Integer(
        default=0, tracking=True,
        help='How far the goal is reached, in percent. A goal served by other goals takes the average of theirs.')
    is_done = fields.Boolean(string='Reached', compute='_compute_is_done', store=True)
    has_children = fields.Boolean(compute='_compute_has_children')

    _progress_range = models.Constraint('CHECK(progress BETWEEN 0 AND 100)',
                                        'The progress of a goal is between 0 and 100 percent.')

    @api.depends('employee_id')
    def _compute_department_id(self):
        for goal in self.filtered('employee_id'):
            goal.department_id = goal.employee_id.department_id

    @api.depends('employee_id', 'department_id')
    def _compute_company_id(self):
        for goal in self:
            goal.company_id = goal.employee_id.company_id or goal.department_id.company_id \
                or goal.company_id or self.env.company

    @api.depends('progress')
    def _compute_is_done(self):
        for goal in self:
            goal.is_done = goal.progress >= 100

    @api.depends('child_ids')
    def _compute_has_children(self):
        for goal in self:
            goal.has_children = bool(goal.child_ids)

    @api.constrains('level', 'employee_id', 'department_id')
    def _check_level(self):
        for goal in self:
            if goal.level == 'employee' and not goal.employee_id:
                raise ValidationError(self.env._('Choose the employee of the goal %s.', goal.name))
            if goal.level == 'department' and not goal.department_id:
                raise ValidationError(self.env._('Choose the department of the goal %s.', goal.name))

    def _is_owner_manager(self):
        """ :return: whether the current user sets this goal: the manager of its employee, or of its department """
        self.ensure_one()
        user = self.env.user
        if self.level == 'employee':
            return self.employee_id.parent_id.user_id == user
        return self.level == 'department' and self.department_id.manager_id.user_id == user

    @api.model_create_multi
    def create(self, vals_list):
        goals = super().create(vals_list)
        goals.parent_id._rollup_progress()
        return goals

    def write(self, vals):
        if not self.env.su:
            # an employee only updates how far their own goals are reached
            if not self.env.user.has_group('hr.group_hr_user') and set(vals) - {'progress'}:
                if not all(goal._is_owner_manager() for goal in self):
                    raise AccessError(self.env._('You update the progress of your goals; your manager sets them.'))
            if 'progress' in vals and self.child_ids:
                raise UserError(self.env._('The progress of a goal served by other goals is the average of theirs.'))
        parents = self.parent_id
        result = super().write(vals)
        if {'progress', 'parent_id'} & set(vals):
            (parents | self.parent_id)._rollup_progress()
        return result

    def unlink(self):
        parents = self.parent_id - self
        result = super().unlink()
        parents.exists()._rollup_progress()
        return result

    def _rollup_progress(self):
        """ A goal served by others takes the average of their progress, and passes it on to the goal it serves. """
        for goal in self.sudo().filtered('child_ids'):
            progress = round(sum(goal.child_ids.mapped('progress')) / len(goal.child_ids))
            if progress != goal.progress:
                goal.progress = progress
