from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class HrExit(models.Model):
    _inherit = 'hr.exit'

    gratuity_scheme_id = fields.Many2one(
        'hr.gratuity.scheme', groups='hr.group_hr_user',
        compute='_compute_gratuity_scheme_id', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    gratuity_date_start = fields.Date(string='Service From', groups='hr.group_hr_user',
                                      compute='_compute_gratuity_date_start', store=True, readonly=False)
    gratuity_wage = fields.Monetary(string='Wage', groups='hr.group_hr_user', currency_field='currency_id',
                                    help='The monthly wage of the last working day.')
    gratuity_years = fields.Float(string='Years of Service', groups='hr.group_hr_user', digits=(16, 2))
    gratuity_days = fields.Float(string='Days of Pay', groups='hr.group_hr_user', digits=(16, 2))
    gratuity_amount = fields.Monetary(string='Gratuity', groups='hr.group_hr_user', tracking=True,
                                      currency_field='currency_id')
    gratuity_explanation = fields.Char(string='How', groups='hr.group_hr_user')

    @api.depends('company_id')
    def _compute_gratuity_scheme_id(self):
        for exit_ in self:
            if not exit_.gratuity_scheme_id:
                exit_.gratuity_scheme_id = self.env['hr.gratuity.scheme'].search(
                    [('company_id', 'in', [False, exit_.company_id.id])], limit=1)

    @api.depends('employee_id')
    def _compute_gratuity_date_start(self):
        for exit_ in self:
            exit_.gratuity_date_start = exit_.employee_id.sudo().first_contract_date

    def action_compute_gratuity(self):
        for exit_ in self:
            if not exit_.gratuity_scheme_id:
                raise UserError(self.env._('Choose the gratuity scheme of %s.', exit_.name))
            if not exit_.gratuity_date_start:
                raise UserError(self.env._('Set the date the service of %s started.', exit_.employee_id.name))
            exit_.write(exit_._gratuity_values())
        return True

    def _gratuity_values(self):
        self.ensure_one()
        end = self.last_working_day + relativedelta(days=1)
        span = relativedelta(end, self.gratuity_date_start)
        years = span.years + span.months / 12.0 + span.days / 365.0
        employee = self.employee_id.sudo()
        version = employee._get_version(self.last_working_day) or employee.version_id
        wage = version.wage
        result = self.gratuity_scheme_id._compute_gratuity(years, wage, self.departure_reason_id)
        return {
            'gratuity_wage': wage,
            'gratuity_years': years,
            'gratuity_days': result['days'],
            'gratuity_amount': self.currency_id.round(result['amount']),
            'gratuity_explanation': result['explanation'],
        }

    def action_done(self):
        for exit_ in self.filtered(lambda e: e.gratuity_scheme_id and e.gratuity_date_start
                                   and not e.gratuity_amount):
            exit_.write(exit_._gratuity_values())
        return super().action_done()
