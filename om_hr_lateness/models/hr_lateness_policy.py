from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

PENALTIES = [
    ('warning', 'Warning'),
    ('fixed', 'Fixed Amount'),
    ('daily_percent', '% of the Daily Wage'),
    ('minutes', 'Minutes at the Hourly Wage'),
]


class HrLatenessPolicy(models.Model):
    """ How late arrivals and early departures are counted and penalised: grace minutes, then a matrix of bands of
    minutes and of occurrences in the month. """
    _name = 'hr.lateness.policy'
    _description = 'Lateness Policy'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,
                                 help='Leave empty to share the policy with all the companies.')
    grace_in = fields.Integer(string='Grace on Arrival (Minutes)', default=10,
                              help='An arrival up to this late is not counted.')
    early_out = fields.Boolean(string='Count Early Departures', default=True)
    grace_out = fields.Integer(string='Grace on Departure (Minutes)', default=10,
                               help='A departure up to this early is not counted.')
    monthly_cap_days = fields.Float(
        string='Monthly Cap (Days of Wage)', default=0.0,
        help='The lateness penalties of a month never go beyond this many days of wage; 0 for no cap.')
    line_ids = fields.One2many('hr.lateness.policy.line', 'policy_id', string='Penalties', copy=True)
    description = fields.Text(translate=True)

    @api.constrains('grace_in', 'grace_out', 'monthly_cap_days')
    def _check_values(self):
        for policy in self:
            if policy.grace_in < 0 or policy.grace_out < 0 or policy.monthly_cap_days < 0:
                raise ValidationError(_('The grace minutes and the cap of %s cannot be negative.', policy.name))

    def _line_for(self, kind, minutes, occurrence):
        """ :return: the penalty of the `occurrence`-th time in the month an employee is `minutes` late, or early
            for a departure: the band of the minutes, the highest occurrence up to it """
        self.ensure_one()
        lines = self.line_ids.filtered(
            lambda line: line.applies_to in ('both', kind) and line.minutes_from <= minutes
            and (not line.minutes_to or minutes <= line.minutes_to) and line.occurrence <= occurrence)
        return lines.sorted(lambda line: (line.occurrence, line.minutes_from))[-1:]


class HrLatenessPolicyLine(models.Model):
    """ One cell of the matrix: from that many minutes, from that occurrence in the month on. """
    _name = 'hr.lateness.policy.line'
    _description = 'Lateness Penalty'
    _order = 'policy_id, applies_to, minutes_from, occurrence'

    policy_id = fields.Many2one('hr.lateness.policy', required=True, ondelete='cascade', index=True)
    applies_to = fields.Selection([('both', 'Both'), ('late_in', 'Late Arrival'), ('early_out', 'Early Departure')],
                                  required=True, default='both')
    minutes_from = fields.Integer(string='From (Minutes)', required=True, default=1)
    minutes_to = fields.Integer(string='To (Minutes)', help='0 for no limit.')
    occurrence = fields.Integer(string='From Occurrence', required=True, default=1,
                                help='The time in the month, counted from 1: 3 is the third time and the ones after, '
                                     'unless a line has a higher occurrence.')
    penalty = fields.Selection(PENALTIES, required=True, default='warning')
    amount = fields.Float(help='The fixed amount.')
    percent = fields.Float(string='% of Daily Wage')
    factor = fields.Float(default=1.0, help='The minutes late are paid back at the hourly wage times this.')

    @api.constrains('minutes_from', 'minutes_to', 'occurrence', 'amount', 'percent', 'factor')
    def _check_values(self):
        for line in self:
            if line.minutes_from < 0 or line.occurrence < 1:
                raise ValidationError(_('A lateness penalty starts from 0 minutes and the first occurrence.'))
            if line.minutes_to and line.minutes_to < line.minutes_from:
                raise ValidationError(_('The band of minutes of a lateness penalty ends after it starts.'))
            if min(line.amount, line.percent, line.factor) < 0:
                raise ValidationError(_('A lateness penalty is not negative.'))

    @api.depends('minutes_from', 'minutes_to', 'occurrence', 'penalty')
    def _compute_display_name(self):
        penalties = dict(PENALTIES)
        for line in self:
            band = '%s-%s' % (line.minutes_from, line.minutes_to) if line.minutes_to else '%s+' % line.minutes_from
            line.display_name = _('%(band)s min, #%(occurrence)s: %(penalty)s', band=band,
                                  occurrence=line.occurrence, penalty=penalties.get(line.penalty))
