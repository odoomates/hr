from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    lateness_auto_penalties = fields.Boolean(
        string='Lateness Penalties Every Month',
        help='On the 1st of each month, the lateness penalties of the month before become payroll adjustments.')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lateness_auto_penalties = fields.Boolean(related='company_id.lateness_auto_penalties', readonly=False)


class HrPayrollAdjustment(models.Model):
    _inherit = 'hr.payroll.adjustment'

    lateness_ids = fields.One2many('hr.lateness', 'adjustment_id', string='Lateness')


class HrLateness(models.Model):
    _inherit = 'hr.lateness'

    adjustment_id = fields.Many2one('hr.payroll.adjustment', string='Payroll Adjustment', ondelete='set null',
                                    index=True, copy=False)
    currency_id = fields.Many2one(related='company_id.currency_id')
    penalty_amount = fields.Monetary(string='Penalty Amount', copy=False,
                                     help='Set when the penalties of the month become a payroll adjustment.')

    # ------------------------------------------------------------------
    # Review: a penalty already taken off a payslip stays
    # ------------------------------------------------------------------

    def _check_not_paid(self):
        paid = self.filtered(lambda lateness: lateness.sudo().adjustment_id.line_ids.filtered(
            lambda line: line.state == 'paid'))
        if paid:
            raise UserError(_('The penalty of %s is taken off a payslip already: refund the payslip first.',
                              paid[0].display_name))

    def _excuse(self, reason):
        self._check_not_paid()
        result = super()._excuse(reason)
        self._recompute_penalties()
        return result

    def action_count_again(self):
        self._check_not_paid()
        result = super().action_count_again()
        self._recompute_penalties()
        return result

    def _recompute_penalties(self):
        """ The months with penalties already turned into adjustments follow a change of their latenesses. """
        for lateness in self.sudo().filtered('adjustment_id'):
            self._compute_penalties(lateness.date.replace(day=1), lateness.employee_id, refresh=False)

    # ------------------------------------------------------------------
    # Penalties
    # ------------------------------------------------------------------

    @api.model
    def _penalty_type(self):
        return self.env.ref('om_hr_lateness_payroll.adjustment_type_lateness')

    def _penalty_amount(self, rates, attendance_based):
        """ :return: the penalty of the lateness, from the wage rates of the employee """
        self.ensure_one()
        line = self.policy_line_id
        if self.state != 'counted' or not line:
            return 0.0
        if line.penalty == 'fixed':
            return line.amount
        if line.penalty == 'daily_percent':
            return rates['daily_wage'] * line.percent / 100
        if line.penalty == 'minutes' and not attendance_based:
            # paid on attendances, the hours missed are already taken off by the Attendance Adjustment rule
            return self.minutes / 60 * rates['hourly_wage'] * line.factor
        return 0.0

    @api.model
    def _compute_penalties(self, month, employees=None, refresh=True):
        """ Turn the penalties of the latenesses of the month into one payroll adjustment per employee, taken by the
            payslip of the month; done again, it follows the latenesses, unless the payslip took it already.
            :return: the adjustments """
        month = month.replace(day=1)
        last_day = fields.Date.add(month, months=1) - timedelta(days=1)
        Lateness = self.sudo()
        if refresh:
            attendances = self.env['hr.attendance'].sudo().search(
                [('date', '>=', month), ('date', '<=', last_day)]
                + ([('employee_id', 'in', employees.ids)] if employees else []))
            attendances.employee_id._compute_lateness(month, last_day)
        domain = [('date', '>=', month), ('date', '<=', last_day)]
        if employees:
            domain.append(('employee_id', 'in', employees.ids))
        latenesses = Lateness.search(domain)
        adjustment_type = self._penalty_type()
        Adjustment = self.env['hr.payroll.adjustment'].sudo()
        existing = Adjustment.search([('type_id', '=', adjustment_type.id), ('date_start', '=', month),
                                      ('state', 'not in', ('cancel', 'refused'))]
                                     + ([('employee_id', 'in', employees.ids)] if employees else []))
        payslip = self.env['hr.payslip']
        result = Adjustment
        for employee in latenesses.employee_id | existing.employee_id:
            adjustment = existing.filtered(lambda a: a.employee_id == employee)[:1]
            if adjustment.line_ids.filtered(lambda line: line.state == 'paid'):
                continue
            of_employee = latenesses.filtered(lambda l: l.employee_id == employee)
            version = employee.version_id
            rates = payslip.new({})._om_wage_rates(version) if version else {'daily_wage': 0.0, 'hourly_wage': 0.0}
            attendance_based = 'attendance_based' in version._fields and version.attendance_based
            currency = employee.company_id.currency_id
            amounts = {lateness: currency.round(lateness._penalty_amount(rates, attendance_based))
                       for lateness in of_employee}
            total = sum(amounts.values())
            policy = employee._lateness_policy()
            if policy.monthly_cap_days:
                total = min(total, currency.round(policy.monthly_cap_days * rates['daily_wage']))
            for lateness, amount in amounts.items():
                lateness.write({'penalty_amount': amount, 'adjustment_id': False})
            if currency.is_zero(total):
                if adjustment:
                    adjustment.line_ids.unlink()
                    adjustment.write({'state': 'cancel', 'approval_state': 'cancel'})
                continue
            values = {
                'amount': total,
                'description': self._penalty_description(of_employee, month),
            }
            if adjustment:
                adjustment.line_ids.unlink()
                adjustment.write({'state': 'draft'})
                adjustment.write(values)
            else:
                adjustment = Adjustment.create(dict(values, employee_id=employee.id, type_id=adjustment_type.id,
                                                    recurrence='once', amount_type='fixed', date_start=month))
            adjustment._compute_lines()
            adjustment.write({'state': 'running', 'approval_state': 'approved'})
            of_employee.filtered(lambda l: amounts[l]).adjustment_id = adjustment
            result |= adjustment
        return result

    @api.model
    def _penalty_description(self, latenesses, month):
        counted = latenesses.filtered(lambda l: l.state == 'counted' and l.penalty and l.penalty != 'warning')
        late = len(counted.filtered(lambda l: l.kind == 'late_in'))
        early = len(counted) - late
        return _('Lateness of %(month)s: %(late)s late arrivals, %(early)s early departures',
                 month=month.strftime('%B %Y'), late=late, early=early)

    @api.model
    def _cron_lateness_penalties(self):
        """ On the 1st, the penalties of the month before, for the companies asking for it. """
        today = fields.Date.context_today(self)
        if today.day != 1:
            return
        companies = self.env['res.company'].search([('lateness_auto_penalties', '=', True)])
        employees = self.env['hr.employee'].search([('company_id', 'in', companies.ids)])
        if employees:
            self._compute_penalties(fields.Date.subtract(today, months=1), employees)
