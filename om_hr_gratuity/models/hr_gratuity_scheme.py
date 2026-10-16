from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OmHrGratuityScheme(models.Model):
    """ How the end of service gratuity is computed: days of pay per year of service, by band of years, part of it
        kept by reason of leaving. """
    _name = 'om.hr.gratuity.scheme'
    _description = 'Gratuity Scheme'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company')
    days_per_month = fields.Float(
        string='Days in a Month of Pay', default=30.0, required=True,
        help='The daily pay is the monthly wage divided by this number, e.g. 30, or 26 working days.')
    min_years = fields.Float(string='Minimum Service (Years)',
                             help='No gratuity below this service. 0: no minimum.')
    max_months = fields.Float(string='Cap (Months of Wage)', help='The gratuity is at most this many monthly wages. '
                                                                   '0: no cap.')
    band_ids = fields.One2many('om.hr.gratuity.band', 'scheme_id', string='Days per Year of Service', copy=True)
    factor_ids = fields.One2many('om.hr.gratuity.factor', 'scheme_id', string='Part Kept by Reason', copy=True)
    note = fields.Text(translate=True)

    def _compute_gratuity(self, years, wage, reason):
        """ :return: dict with the days of pay earned, the part kept in %, the amount and an explanation """
        self.ensure_one()
        explanation = []
        if years < self.min_years:
            return {'days': 0.0, 'factor': 0.0, 'amount': 0.0, 'explanation': _(
                '%(years).2f years of service, below the minimum of %(min)s.', years=years, min=self.min_years)}
        days = 0.0
        for band in self.band_ids.sorted('from_years'):
            top = band.to_years or years
            in_band = max(0.0, min(years, top) - band.from_years)
            if in_band:
                days += in_band * band.days_per_year
                explanation.append(_('%(years).2f years × %(days)s days', years=in_band, days=band.days_per_year))
        amount = days * wage / self.days_per_month
        factor = self.factor_ids._factor_for(years, reason)
        amount = amount * factor / 100.0
        if factor != 100.0:
            explanation.append(_('%(factor)s%% kept for %(reason)s', factor=factor, reason=reason.name))
        if self.max_months and amount > self.max_months * wage:
            amount = self.max_months * wage
            explanation.append(_('capped at %s months of wage', self.max_months))
        return {'days': days, 'factor': factor, 'amount': amount, 'explanation': ', '.join(explanation)}


class OmHrGratuityBand(models.Model):
    _name = 'om.hr.gratuity.band'
    _description = 'Gratuity Band'
    _order = 'scheme_id, from_years'

    scheme_id = fields.Many2one('om.hr.gratuity.scheme', required=True, ondelete='cascade', index=True)
    from_years = fields.Float(string='From (Years)', required=True)
    to_years = fields.Float(string='To (Years)', help='0: every year beyond.')
    days_per_year = fields.Float(string='Days of Pay per Year', required=True)

    @api.constrains('from_years', 'to_years')
    def _check_years(self):
        for band in self:
            if band.to_years and band.to_years <= band.from_years:
                raise ValidationError(_('A band of years ends after it starts.'))


class OmHrGratuityFactor(models.Model):
    _name = 'om.hr.gratuity.factor'
    _description = 'Gratuity Part Kept'
    _order = 'scheme_id, from_years'

    scheme_id = fields.Many2one('om.hr.gratuity.scheme', required=True, ondelete='cascade', index=True)
    departure_reason_ids = fields.Many2many('hr.departure.reason', string='Reasons', required=True)
    from_years = fields.Float(string='From (Years)')
    to_years = fields.Float(string='To (Years)', help='0: every year beyond.')
    factor = fields.Float(string='Part Kept (%)', required=True, default=100.0)

    def _factor_for(self, years, reason):
        """ :return: the part kept by the first line matching the reason and the service; 100 when none does """
        for line in self.sorted('from_years'):
            if reason in line.departure_reason_ids and line.from_years <= years \
                    and (not line.to_years or years < line.to_years):
                return line.factor
        return 100.0
