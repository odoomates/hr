from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_duration


def shift_segments(hour_from, hour_to, break_from=0.0, break_to=0.0):
    """ :return: the worked parts of a shift as [(day offset, hour from, hour to)], a shift ending at or before its
        start ending the next day, without its break; 24 is the end of a day, as in the working schedules """
    overnight = hour_to <= hour_from
    end = hour_to + (24 if overnight else 0)
    pieces = [(hour_from, end)]
    if break_to != break_from:
        start_break = break_from + (24 if overnight and break_from < hour_from else 0)
        end_break = break_to + (24 if overnight and break_to <= hour_from else 0)
        if hour_from <= start_break < end_break <= end:
            pieces = [(hour_from, start_break), (end_break, end)]
    segments = []
    for start, stop in pieces:
        while start < stop:
            day = int(start // 24)
            limit = min(stop, (day + 1) * 24)
            if limit > start:
                segments.append((day, start - day * 24, limit - day * 24))
            start = limit
    return [segment for segment in segments if segment[2] > segment[1]]


class OmHrShiftTemplate(models.Model):
    """ A kind of shift, e.g. Morning 06:00-14:00, assigned on the roster in a click. """
    _name = 'om.hr.shift.template'
    _description = 'Shift Template'
    _order = 'sequence, hour_from'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(string='Short Name', required=True, size=4, help='Shown on the roster, e.g. M for Morning.')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    hour_from = fields.Float(string='From', required=True, default=8.0)
    hour_to = fields.Float(string='To', required=True, default=16.0,
                           help='At or before the start, the shift ends the next day.')
    break_from = fields.Float(string='Break From')
    break_to = fields.Float(string='Break To', help='The unpaid break; the same as Break From for none.')
    hours = fields.Float(compute='_compute_hours', string='Hours Worked')
    color = fields.Integer(default=1)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,
                                 help='Leave empty to share the template with all the companies.')
    department_ids = fields.Many2many('hr.department', string='Departments',
                                      help='The departments planning this shift; empty for all.')
    job_ids = fields.Many2many('hr.job', string='Job Positions',
                               help='The positions working this shift, e.g. for the open shifts; empty for all.')
    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', string='Time Type',
        help='The work entries of the shift, e.g. night work paid at its own rate; the usual type when empty.')
    allowance = fields.Monetary(string='Allowance per Shift',
                                help='Paid for each shift worked, with the payroll.')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    @api.depends('hour_from', 'hour_to', 'break_from', 'break_to')
    def _compute_hours(self):
        for template in self:
            template.hours = sum(stop - start for _day, start, stop in shift_segments(
                template.hour_from, template.hour_to, template.break_from, template.break_to))

    @api.depends('name', 'hour_from', 'hour_to')
    def _compute_display_name(self):
        for template in self:
            template.display_name = '%s (%s-%s)' % (template.name, format_duration(template.hour_from),
                                                    format_duration(template.hour_to))

    @api.constrains('hour_from', 'hour_to', 'break_from', 'break_to')
    def _check_hours(self):
        for template in self:
            hours = (template.hour_from, template.hour_to, template.break_from, template.break_to)
            if any(not 0 <= hour <= 24 for hour in hours):
                raise ValidationError(_('The hours of %s are between 00:00 and 24:00.', template.name))
            if template.hour_from == template.hour_to:
                raise ValidationError(_('The shift %s starts and ends at the same time.', template.name))
            if template.break_from != template.break_to and template.hours >= template._raw_hours():
                raise ValidationError(_('The break of %s is not within the shift.', template.name))

    def _raw_hours(self):
        self.ensure_one()
        return sum(stop - start for _day, start, stop in shift_segments(self.hour_from, self.hour_to))

    def _shift_values(self):
        self.ensure_one()
        return {'template_id': self.id, 'hour_from': self.hour_from, 'hour_to': self.hour_to,
                'break_from': self.break_from, 'break_to': self.break_to}
