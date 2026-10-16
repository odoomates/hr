# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrVersion(models.Model):
    """
    Employee contract based on the visa, work permits
    allows to configure different Salary structure
    """
    _inherit = 'hr.version'
    _description = 'Employee Contract'


    struct_id = fields.Many2one('hr.payroll.structure', string='Salary Structure', check_company=True)
    schedule_pay = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
    ], string='Scheduled Pay', index=True, default='monthly',
    help="Defines the frequency of the wage payment.")
    # payroll officers compute the payslips from the wage
    wage = fields.Monetary(groups="hr.group_hr_manager,om_hr_payroll.group_hr_payroll_user")
    wage_type = fields.Selection([
        ('monthly', 'Fixed Wage'),
        ('hourly', 'Hourly Wage'),
    ], string='Wage Type', default='monthly', required=True, tracking=True,
        groups="hr.group_hr_manager,om_hr_payroll.group_hr_payroll_user",
        help='Fixed Wage: the wage of the month. Hourly Wage: the hours paid in the period times the hourly wage.')
    hourly_wage = fields.Monetary(tracking=True, groups="hr.group_hr_manager,om_hr_payroll.group_hr_payroll_user",
                                  help='Paid per hour worked, or per hour of paid time off at its rate.')

    @api.model
    def _company_checked_fields(self):
        return super()._company_checked_fields() + ['struct_id']

    @api.onchange('wage_type')
    def _onchange_wage_type(self):
        if self.wage_type == 'hourly':
            self.wage = 0.0

    @api.constrains('wage_type', 'wage')
    def _check_hourly_wage(self):
        for version in self.sudo():
            if version.wage_type == 'hourly' and version.wage:
                raise ValidationError(self.env._(
                    'The contract of %s is paid by the hour: set its fixed wage to 0, the Hourly Pay rule pays it.',
                    version.employee_id.name))
    salary_component_ids = fields.One2many(
        'hr.version.salary.component', 'version_id', string='Salary Components', copy=True,
        help='What the employee is paid besides the wage, e.g. a housing or a transport component. '
             'The salary rules read them with components.<CODE>.')

    @api.model
    def _get_whitelist_fields_from_template(self):
        res = super()._get_whitelist_fields_from_template()
        res.append('struct_id')
        return res

    def get_all_structures(self):
        """
        @return: the structures linked to the given contracts, ordered by hierachy (parent=False first,
                 then first level children and so on) and without duplicata
        """
        structures = self.mapped('struct_id')
        if not structures:
            return []
        # keep the order: a rule of a child structure overrides the rule of the same code of its parent, which
        # a set would leave to the ids of the structures
        return list(dict.fromkeys(structures._get_parent_structure().ids))

    def get_component(self, code):
        """ :return: the amount of the salary component `code` on the version, 0.0 when it has none """
        self.ensure_one()
        component = self.salary_component_ids.filtered(lambda line: line.code == code)[:1]
        return component.amount

    def get_attribute(self, code, attribute):
        return self.env['hr.contract.advantage.template'].search([('code', '=', code)], limit=1)[attribute]

    def set_attribute_value(self, code, active):
        for contract in self:
            if active:
                value = self.env['hr.contract.advantage.template'].search([('code', '=', code)], limit=1).default_value
                contract[code] = value
            else:
                contract[code] = 0.0


class HrContractAdvantageTemplate(models.Model):
    _name = 'hr.contract.advantage.template'
    _description = "Employee's Advantage on Contract"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    company_id = fields.Many2one('res.company', help='Leave empty to share the advantage with all the companies.')
    lower_bound = fields.Float('Lower Bound', help="Lower bound authorized by the employer for this advantage")
    upper_bound = fields.Float('Upper Bound', help="Upper bound authorized by the employer for this advantage")
    default_value = fields.Float('Default value for this advantage')

