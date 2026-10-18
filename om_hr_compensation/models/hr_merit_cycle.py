from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from .hr_version import BAND_POSITIONS, band_position

# what a manager changes on the proposal of an employee of their team
MANAGER_WRITABLE = {'proposed_percent', 'proposed_wage', 'note'}


class HrMeritCycle(models.Model):
    """ The yearly raises: each department gets a budget, a share of what it pays today; the managers propose the
    raises of their team within it, HR approves them, and the approved raises become new contract versions. """
    _name = 'hr.merit.cycle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Merit Cycle'
    _check_company_auto = True
    _order = 'date_effective desc, id desc'

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date_effective = fields.Date(string='Effective From', required=True, tracking=True,
                                 help='The date of the contract versions of the approved raises.')
    date_deadline = fields.Date(string='Proposals By', tracking=True)
    budget_percent = fields.Float(
        string='Budget (%)', default=3.0, tracking=True,
        help='The budget of each department: this share of the monthly wages it pays today.')
    department_ids = fields.Many2many('hr.department', string='Departments', check_company=True,
                                      help='Leave empty for all the departments of the company.')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Proposals'),
        ('review', 'HR Review'),
        ('done', 'Applied'),
        ('cancel', 'Cancelled'),
    ], required=True, default='draft', copy=False, tracking=True)
    line_ids = fields.One2many('hr.merit.cycle.line', 'cycle_id', string='Employees')
    budget_ids = fields.One2many('hr.merit.cycle.budget', 'cycle_id', string='Budgets')
    budget_total = fields.Monetary(compute='_compute_totals')
    increase_total = fields.Monetary(string='Proposed', compute='_compute_totals')

    @api.depends('budget_ids.budget', 'line_ids.increase', 'line_ids.state')
    def _compute_totals(self):
        for cycle in self:
            cycle.budget_total = sum(cycle.budget_ids.mapped('budget'))
            cycle.increase_total = sum(cycle.line_ids.filtered(lambda line: line.state != 'refused').mapped('increase'))

    def _get_employees(self):
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id), ('wage', '>', 0)]
        if self.department_ids:
            domain.append(('department_id', 'child_of', self.department_ids.ids))
        return self.env['hr.employee'].search(domain)

    def _line_values(self, employee):
        """ :return: the values of the line of `employee`, from their current contract version """
        version = employee.version_id
        return {
            'cycle_id': self.id,
            'employee_id': employee.id,
            'department_id': employee.department_id.id,
            'manager_id': employee.parent_id.id,
            'job_id': version.job_id.id,
            'salary_grade_id': version.salary_grade_id.id,
            'current_wage': version.wage,
            'proposed_percent': 0.0,
        }

    def action_generate(self):
        """ One line per employee paid, with their wage today, and the budget of each department. """
        for cycle in self:
            if cycle.state != 'draft':
                raise UserError(self.env._('%s is already under way.', cycle.name))
            employees = cycle._get_employees() - cycle.line_ids.employee_id
            self.env['hr.merit.cycle.line'].create([cycle._line_values(employee) for employee in employees])
            cycle._update_budgets()
        return True

    def _update_budgets(self):
        Budget = self.env['hr.merit.cycle.budget']
        for cycle in self:
            for department in cycle.line_ids.department_id - cycle.budget_ids.department_id:
                Budget.create({'cycle_id': cycle.id, 'department_id': department.id,
                               'percent': cycle.budget_percent})

    def action_open(self):
        for cycle in self:
            if not cycle.line_ids:
                raise UserError(self.env._('Generate the employees of %s first.', cycle.name))
            cycle.state = 'open'
            for manager in cycle.line_ids.manager_id.user_id:
                cycle.activity_schedule('mail.mail_activity_data_todo', user_id=manager.id,
                                        date_deadline=cycle.date_deadline or fields.Date.context_today(cycle),
                                        summary=self.env._('Propose the raises of your team'))
        return True

    def action_review(self):
        self.write({'state': 'review'})
        self.activity_unlink(['mail.mail_activity_data_todo'])
        return True

    def action_back_to_open(self):
        self.write({'state': 'open'})
        return True

    def action_approve_all(self):
        self.line_ids.filtered(lambda line: line.state == 'proposed').write({'state': 'approved'})
        return True

    def action_apply(self):
        """ A new version of the contract of each employee with an approved raise, from the effective date. """
        for cycle in self:
            if cycle.state != 'review':
                raise UserError(self.env._('Review %s before applying it.', cycle.name))
            for line in cycle.line_ids.filtered(lambda line: line.state == 'approved' and line.increase > 0):
                version = line.employee_id.create_version({'date_version': cycle.date_effective})
                version.wage = line.proposed_wage
                line.version_id = version
            cycle.state = 'done'
        return True

    def action_cancel(self):
        self.filtered(lambda cycle: cycle.state != 'done').write({'state': 'cancel'})
        return True

    def action_draft(self):
        self.filtered(lambda cycle: cycle.state == 'cancel').write({'state': 'draft'})
        return True


class HrMeritCycleBudget(models.Model):
    """ What a department may spend on the raises of a cycle, and what its managers proposed. """
    _name = 'hr.merit.cycle.budget'
    _description = 'Merit Cycle Budget'
    _order = 'department_id'

    cycle_id = fields.Many2one('hr.merit.cycle', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='cycle_id.company_id', store=True)
    currency_id = fields.Many2one(related='cycle_id.currency_id')
    department_id = fields.Many2one('hr.department', required=True)
    manager_id = fields.Many2one(related='department_id.manager_id')
    percent = fields.Float(string='Budget (%)')
    payroll = fields.Monetary(string='Wages Today', compute='_compute_amounts')
    budget = fields.Monetary(compute='_compute_amounts')
    proposed = fields.Monetary(compute='_compute_amounts')
    remaining = fields.Monetary(compute='_compute_amounts')

    _department_uniq = models.Constraint('unique(cycle_id, department_id)',
                                         'A department has one budget per merit cycle.')

    @api.depends('percent', 'cycle_id.line_ids.current_wage', 'cycle_id.line_ids.increase',
                 'cycle_id.line_ids.state')
    def _compute_amounts(self):
        for budget in self:
            lines = budget.cycle_id.line_ids.filtered(lambda line: line.department_id == budget.department_id)
            budget.payroll = sum(lines.mapped('current_wage'))
            budget.budget = budget.currency_id.round(budget.payroll * budget.percent / 100)
            budget.proposed = sum(lines.filtered(lambda line: line.state != 'refused').mapped('increase'))
            budget.remaining = budget.budget - budget.proposed


class HrMeritCycleLine(models.Model):
    """ The raise proposed for an employee in a merit cycle. """
    _name = 'hr.merit.cycle.line'
    _description = 'Merit Cycle Line'
    _check_company_auto = True
    _order = 'department_id, employee_id'

    cycle_id = fields.Many2one('hr.merit.cycle', required=True, index=True, ondelete='cascade')
    company_id = fields.Many2one(related='cycle_id.company_id', store=True)
    currency_id = fields.Many2one(related='cycle_id.currency_id')
    cycle_state = fields.Selection(related='cycle_id.state', string='Cycle Status')
    employee_id = fields.Many2one('hr.employee', required=True, check_company=True)
    department_id = fields.Many2one('hr.department')
    manager_id = fields.Many2one('hr.employee')
    job_id = fields.Many2one('hr.job')
    salary_grade_id = fields.Many2one('hr.salary.grade', string='Grade')
    current_wage = fields.Monetary(string='Wage Today')
    compa_ratio = fields.Float(string='Compa-Ratio', compute='_compute_band', store=True, digits=(16, 2))
    band_position = fields.Selection(BAND_POSITIONS, string='In Band', compute='_compute_band', store=True)
    proposed_percent = fields.Float(string='Raise (%)', digits=(16, 2))
    proposed_wage = fields.Monetary(string='New Wage', compute='_compute_proposed_wage',
                                    inverse='_inverse_proposed_wage', store=True)
    increase = fields.Monetary(compute='_compute_increase', store=True)
    new_compa_ratio = fields.Float(string='New Compa-Ratio', compute='_compute_band', store=True, digits=(16, 2))
    state = fields.Selection([
        ('proposed', 'Proposed'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
    ], required=True, default='proposed')
    note = fields.Char()
    version_id = fields.Many2one('hr.version', string='Contract Version', readonly=True)

    _employee_uniq = models.Constraint('unique(cycle_id, employee_id)',
                                       'An employee has one line per merit cycle.')

    @api.depends('current_wage', 'proposed_percent')
    def _compute_proposed_wage(self):
        for line in self:
            line.proposed_wage = line.currency_id.round(line.current_wage * (1 + line.proposed_percent / 100))

    def _inverse_proposed_wage(self):
        for line in self:
            line.proposed_percent = (line.proposed_wage / line.current_wage - 1) * 100 if line.current_wage else 0.0

    @api.depends('current_wage', 'proposed_wage')
    def _compute_increase(self):
        for line in self:
            line.increase = line.proposed_wage - line.current_wage

    @api.depends('current_wage', 'proposed_wage', 'salary_grade_id.wage_min', 'salary_grade_id.wage_mid',
                 'salary_grade_id.wage_max')
    def _compute_band(self):
        for line in self:
            grade = line.salary_grade_id
            line.compa_ratio = line.current_wage / grade.wage_mid if grade.wage_mid else 0.0
            line.new_compa_ratio = line.proposed_wage / grade.wage_mid if grade.wage_mid else 0.0
            line.band_position = band_position(line.current_wage, grade)

    def write(self, vals):
        if not self.env.su and not self.env.user.has_group('hr.group_hr_manager'):
            for line in self:
                if line.manager_id.user_id != self.env.user or set(vals) - MANAGER_WRITABLE:
                    raise AccessError(self.env._('You propose the raises of your own team only.'))
                if line.cycle_id.state != 'open':
                    raise UserError(self.env._('%s is not open for proposals.', line.cycle_id.name))
        result = super().write(vals)
        if not self.env.su and not self.env.user.has_group('hr.group_hr_manager'):
            self._check_budget()
        return result

    def _check_budget(self):
        """ A manager keeps the raises of a department within its budget; an HR administrator may go beyond it. """
        # read as the super user: a manager of a team is not always the manager of its department
        for budget in self.sudo().cycle_id.budget_ids.filtered(
                lambda budget: budget.department_id in self.department_id):
            if budget.remaining < 0:
                raise UserError(self.env._(
                    'The raises of %(department)s go %(over)s over its budget of %(budget)s.',
                    department=budget.department_id.name,
                    over=budget.currency_id.format(-budget.remaining),
                    budget=budget.currency_id.format(budget.budget)))

    def action_approve(self):
        self.write({'state': 'approved'})
        return True

    def action_refuse(self):
        self.write({'state': 'refused'})
        return True
