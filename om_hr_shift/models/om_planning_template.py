from datetime import datetime, time, timedelta

from odoo import api, fields, models


def shift_segments(start, stop, break_from=0.0, break_hours=0.0):
    """ :param start: the local start of a shift, a naive datetime
        :param stop: its local end
        :param break_from: the hour the unpaid break starts; outside the shift, the break is in its middle
        :param break_hours: the length of the break
        :return: the worked parts of the shift as [(date, hour from, hour to)], cut at midnight, without the break;
            24 is the end of a day, as in the working schedules """
    pieces = [(start, stop)]
    if break_hours and 0 < break_hours < (stop - start).total_seconds() / 3600:
        length = timedelta(hours=break_hours)
        begin = datetime.combine(start.date(), time.min) + timedelta(hours=break_from)
        if begin < start:
            begin += timedelta(days=1)
        if begin + length > stop:
            begin = start + (stop - start - length) / 2
        pieces = [(start, begin), (begin + length, stop)]
    segments = []
    for begin, end in pieces:
        while begin < end:
            midnight = datetime.combine(begin.date() + timedelta(days=1), time.min)
            limit = min(end, midnight)
            hour_from = begin.hour + begin.minute / 60 + begin.second / 3600
            hour_to = 24.0 if limit == midnight else limit.hour + limit.minute / 60 + limit.second / 3600
            if hour_to > hour_from:
                segments.append((begin.date(), round(hour_from, 4), round(hour_to, 4)))
            begin = limit
    return segments


class OmPlanningTemplate(models.Model):
    _inherit = 'om.planning.template'

    break_from = fields.Float(string='Break From',
                              help='The hour the unpaid break starts; outside the shift, the break is in its middle.')
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
    old_template_id = fields.Integer(string='Former Shift Template', readonly=True, copy=False,
                                     index='btree_not_null')

    @api.onchange('start_time', 'end_time', 'break_hours')
    def _onchange_break_from(self):
        if self.break_hours and not self.break_from:
            span = (self.end_time - self.start_time) % 24 or 24
            self.break_from = (self.start_time + (span - self.break_hours) / 2) % 24

    def _shift_values(self, day, employee=None):
        """ :return: the values of a slot of the template on `day`, for `employee` (an open slot without) """
        self.ensure_one()
        resource = employee.resource_id if employee else self.env['resource.resource']
        tz = resource.tz or self.env.context.get('tz') or self.env.user.tz or 'UTC'
        start, stop = self._get_period(day, tz)
        values = {
            'template_id': self.id,
            'start_datetime': start,
            'end_datetime': stop,
            'break_hours': self.break_hours,
            'break_from': self.break_from,
            'resource_ids': [fields.Command.set(resource.ids)],
        }
        if self.role_id:
            values['role_id'] = self.role_id.id
        if employee:
            values['company_id'] = employee.company_id.id
        return values
