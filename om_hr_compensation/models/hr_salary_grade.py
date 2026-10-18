from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrSalaryGrade(models.Model):
    """ A pay grade, e.g. G5: the band of monthly wages paid for the job positions of the grade. """
    _name = 'hr.salary.grade'
    _inherit = ['mail.thread']
    _description = 'Salary Grade'
    _check_company_auto = True
    _order = 'sequence, wage_mid, id'

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    wage_min = fields.Monetary(string='Minimum', required=True, tracking=True)
    wage_mid = fields.Monetary(
        string='Midpoint', tracking=True, compute='_compute_wage_mid', store=True, readonly=False, precompute=True,
        help='The market rate of the grade: a compa-ratio of 1.00 pays exactly this. By default halfway between '
             'the minimum and the maximum.')
    wage_max = fields.Monetary(string='Maximum', required=True, tracking=True)
    job_ids = fields.One2many('hr.job', 'salary_grade_id', string='Job Positions')
    note = fields.Text()

    _name_company_uniq = models.Constraint('unique(name, company_id)',
                                           'The name of a salary grade must be unique per company.')

    @api.depends('wage_min', 'wage_max')
    def _compute_wage_mid(self):
        for grade in self:
            grade.wage_mid = (grade.wage_min + grade.wage_max) / 2

    @api.constrains('wage_min', 'wage_mid', 'wage_max')
    def _check_band(self):
        for grade in self:
            if not 0 <= grade.wage_min <= grade.wage_mid <= grade.wage_max:
                raise ValidationError(self.env._(
                    'The band of %s goes up from the minimum to the midpoint to the maximum.', grade.name))


class HrJob(models.Model):
    _inherit = 'hr.job'

    salary_grade_id = fields.Many2one('hr.salary.grade', check_company=True,
                                      groups='hr.group_hr_user', tracking=True)
