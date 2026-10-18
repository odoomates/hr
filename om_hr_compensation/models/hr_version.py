from odoo import api, fields, models

# where a wage sits in the band of its grade
BAND_POSITIONS = [
    ('below', 'Below the Band'),
    ('lower', 'Lower Third'),
    ('middle', 'Middle Third'),
    ('upper', 'Upper Third'),
    ('above', 'Above the Band'),
]


def band_position(wage, grade):
    """ :return: where `wage` sits in the band of `grade`, a key of BAND_POSITIONS, or False without a band """
    if not grade or grade.wage_max <= 0:
        return False
    if wage < grade.wage_min:
        return 'below'
    if wage > grade.wage_max:
        return 'above'
    width = grade.wage_max - grade.wage_min
    share = (wage - grade.wage_min) / width if width else 0.5
    return 'lower' if share < 1 / 3 else 'middle' if share <= 2 / 3 else 'upper'


class HrVersion(models.Model):
    _inherit = 'hr.version'

    salary_grade_id = fields.Many2one(related='job_id.salary_grade_id', store=True, groups='hr.group_hr_manager')
    compa_ratio = fields.Float(
        compute='_compute_band', store=True, groups='hr.group_hr_manager', aggregator='avg', digits=(16, 2),
        help='The wage divided by the midpoint of the grade: 1.00 pays the midpoint, 0.90 is 10% below it.')
    band_position = fields.Selection(
        BAND_POSITIONS, compute='_compute_band', store=True, groups='hr.group_hr_manager',
        help='Where the wage sits in the band of the grade of the job position.')

    @api.depends('wage', 'salary_grade_id.wage_min', 'salary_grade_id.wage_mid', 'salary_grade_id.wage_max')
    def _compute_band(self):
        for version in self:
            grade = version.salary_grade_id
            version.compa_ratio = version.wage / grade.wage_mid if grade.wage_mid else 0.0
            version.band_position = band_position(version.wage, grade)

    @api.model
    def action_open_pay_position(self):
        """ The current versions of the employees on a salary grade, where their wage sits in its band. """
        action = self.env['ir.actions.act_window']._for_xml_id('om_hr_compensation.hr_version_action_pay_position')
        employees = self.env['hr.employee'].search([('company_id', 'in', self.env.companies.ids)])
        action['domain'] = [('id', 'in', employees.version_id.ids), ('salary_grade_id', '!=', False)]
        return action
