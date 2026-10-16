from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_duration

from .hr_shift_template import shift_segments


class HrShift(models.Model):
    """ A shift of an employee on a day, or an open shift no one works yet. Published, it is written on the roster
    schedule of the employee, which the time off, the work entries, the overtime and the payroll all read. """
    _name = 'hr.shift'
    _inherit = ['mail.thread']
    _description = 'Shift'
    _order = 'date, hour_from, id'

    employee_id = fields.Many2one('hr.employee', index=True, tracking=True,
                                  help='Empty for an open shift, which the employees may claim.')
    company_id = fields.Many2one('res.company', required=True, index=True,
                                 compute='_compute_company_id', store=True, readonly=False, precompute=True)
    department_id = fields.Many2one('hr.department', compute='_compute_department_id',
                                    store=True, readonly=False, index=True)
    template_id = fields.Many2one('hr.shift.template', string='Shift Template', tracking=True)
    date = fields.Date(required=True, index=True, tracking=True)
    hour_from = fields.Float(string='From', required=True, tracking=True)
    hour_to = fields.Float(string='To', required=True, tracking=True, help='At or before the start: the next day.')
    break_from = fields.Float()
    break_to = fields.Float()
    hours = fields.Float(compute='_compute_hours', store=True, aggregator='sum')
    start = fields.Datetime(compute='_compute_start', store=True)
    stop = fields.Datetime(compute='_compute_start', store=True)
    color = fields.Integer(related='template_id.color')
    state = fields.Selection([('draft', 'Draft'), ('published', 'Published')], required=True, default='draft',
                             index=True, tracking=True, copy=False)
    note = fields.Text()
    attendance_ids = fields.Many2many('resource.calendar.attendance', string='Schedule Lines', copy=False,
                                      readonly=True)
    warning = fields.Text(compute='_compute_warning', string='Warnings')

    @api.depends('employee_id')
    def _compute_company_id(self):
        for shift in self:
            shift.company_id = shift.employee_id.company_id or shift.company_id or self.env.company

    @api.depends('employee_id')
    def _compute_department_id(self):
        for shift in self:
            if shift.employee_id:
                shift.department_id = shift.employee_id.department_id

    @api.depends('hour_from', 'hour_to', 'break_from', 'break_to')
    def _compute_hours(self):
        for shift in self:
            shift.hours = sum(stop - start for _day, start, stop in shift._segments())

    @api.depends('date', 'hour_from', 'hour_to', 'employee_id.tz', 'company_id')
    def _compute_start(self):
        for shift in self:
            if not shift.date:
                shift.start = shift.stop = False
                continue
            tz = shift._tz()
            overnight = shift.hour_to <= shift.hour_from
            shift.start = self._to_utc(shift.date, shift.hour_from, tz)
            shift.stop = self._to_utc(shift.date + timedelta(days=1 if overnight else 0), shift.hour_to, tz)

    @api.depends('employee_id', 'date', 'hour_from', 'hour_to')
    def _compute_display_name(self):
        for shift in self:
            who = shift.employee_id.name or self.env._('Open Shift')
            shift.display_name = '%s, %s %s-%s' % (who, shift.date or '', format_duration(shift.hour_from),
                                                   format_duration(shift.hour_to))

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.update({key: value for key, value in self.template_id._shift_values().items()
                         if key != 'template_id'})

    @api.constrains('hour_from', 'hour_to', 'break_from', 'break_to')
    def _check_hours(self):
        for shift in self:
            if any(not 0 <= hour <= 24 for hour in (shift.hour_from, shift.hour_to, shift.break_from, shift.break_to)):
                raise ValidationError(self.env._('The hours of a shift are between 00:00 and 24:00.'))
            if shift.hour_from == shift.hour_to:
                raise ValidationError(self.env._('A shift starts and ends at different times.'))

    def _segments(self):
        self.ensure_one()
        return shift_segments(self.hour_from, self.hour_to, self.break_from, self.break_to)

    def _tz(self):
        self.ensure_one()
        name = self.employee_id.sudo()._get_tz(date=self.date) if self.employee_id else (
            self.env.user.tz or self.company_id.partner_id.tz or 'UTC')
        return ZoneInfo(name or 'UTC')

    @staticmethod
    def _to_utc(day, hour, tz):
        moment = datetime.combine(day, time.min) + timedelta(hours=hour)
        return moment.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    @api.depends('employee_id', 'start', 'stop')
    def _compute_warning(self):
        warnings = self._check()
        for shift in self:
            shift.warning = '\n'.join(warnings.get(shift.id, [])) or False

    def _check(self):
        """ :return: {shift id: [warnings]}: time off or public holiday, unavailability, rest, hours of the week,
            overlap, before the roster of the employee started """
        result = defaultdict(list)
        shifts = self.filtered(lambda s: s.employee_id and s.start and s.stop and s.id)
        if not shifts:
            return result
        Shift = self.env['hr.shift'].sudo()
        employees = shifts.employee_id.sudo()
        first = min(shifts.mapped('start')) - timedelta(days=7)
        last = max(shifts.mapped('stop')) + timedelta(days=7)
        others = Shift.search([('employee_id', 'in', employees.ids), ('stop', '>', first), ('start', '<', last)])
        leaves = self.env['resource.calendar.leaves'].sudo().search([
            ('date_from', '<', last), ('date_to', '>', first),
            '|', ('resource_id', 'in', employees.resource_id.ids),
            '&', ('resource_id', '=', False), ('company_id', 'in', employees.company_id.ids + [False])])
        unavailable = self.env['hr.shift.unavailability'].sudo().search([
            ('employee_id', 'in', employees.ids), ('date_from', '<=', max(shifts.mapped('date'))),
            ('date_to', '>=', min(shifts.mapped('date')))])
        for shift in shifts:
            employee = shift.employee_id.sudo()
            company = employee.company_id
            calendars = (employee.resource_calendar_id, employee.roster_calendar_id)
            for leave in leaves.filtered(lambda time_off: (
                    time_off.date_from < shift.stop and time_off.date_to > shift.start and (
                        time_off.resource_id == employee.resource_id
                        or (not time_off.resource_id and time_off.company_id in (company, self.env['res.company'])
                            and (not time_off.calendar_id or time_off.calendar_id in calendars))))):
                result[shift.id].append(self.env._('Time off: %s', leave.name or self.env._('Public Holiday')))
            for unavailability in unavailable.filtered(
                    lambda u: u.employee_id == employee and u.date_from <= shift.date <= u.date_to):
                result[shift.id].append(self.env._('Unavailable: %s',
                                                   unavailability.reason or self.env._('no reason given')))
            mine = others.filtered(lambda s: s.employee_id == employee and s != shift)
            for other in mine.filtered(lambda s: s.start < shift.stop and s.stop > shift.start):
                result[shift.id].append(self.env._('Overlaps %s', other.display_name))
            rest = company.shift_min_rest
            if rest:
                for other in mine.filtered(lambda s: not (s.start < shift.stop and s.stop > shift.start)):
                    gap = (shift.start - other.stop) if other.stop <= shift.start else (other.start - shift.stop)
                    if gap < timedelta(hours=rest):
                        result[shift.id].append(self.env._('Only %(hours)s of rest with %(shift)s',
                                                           hours=format_duration(gap.total_seconds() / 3600),
                                                           shift=other.display_name))
            if company.shift_max_week_hours:
                monday = shift.date - timedelta(days=shift.date.weekday())
                week = (mine | shift).filtered(lambda s: monday <= s.date < monday + timedelta(days=7))
                total = sum(week.mapped('hours'))
                if total > company.shift_max_week_hours:
                    result[shift.id].append(self.env._('%(hours)s hours in the week, %(max)s at most',
                                                       hours=format_duration(total),
                                                       max=format_duration(company.shift_max_week_hours)))
            if employee.roster_date_start and shift.date < employee.roster_date_start:
                result[shift.id].append(self.env._('Before the roster of %(employee)s starts, on %(date)s',
                                                   employee=employee.name, date=employee.roster_date_start))
        return result

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def _check_planner(self):
        if not self.env.user.has_group('om_hr_shift.group_shift_planner'):
            raise UserError(self.env._('Only the shift planners publish and change the shifts.'))

    def action_publish(self):
        """ Publish the draft shifts; with warnings, the planner confirms first. """
        self._check_planner()
        shifts = self.filtered(lambda s: s.state == 'draft')
        if not shifts:
            raise UserError(self.env._('Nothing to publish: the shifts are published already.'))
        warnings = shifts._check()
        if warnings and not self.env.context.get('om_shift_override'):
            return {
                'type': 'ir.actions.act_window',
                'name': self.env._('Publish Shifts'),
                'res_model': 'hr.shift.publish.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_shift_ids': shifts.ids},
            }
        shifts._publish(warnings, self.env.context.get('om_shift_override_reason'))
        return True

    def _publish(self, warnings=None, reason=None):
        warnings = warnings or {}
        for shift in self:
            if shift.employee_id:
                shift._write_schedule()
            if warnings.get(shift.id):
                shift.message_post(body=self.env._('Published despite: %(warnings)s. %(reason)s',
                                                   warnings='; '.join(warnings[shift.id]), reason=reason or ''),
                                   subtype_xmlid='mail.mt_note')
        self.write({'state': 'published'})
        self._notify(self.env._('Your shifts are published'))

    def _write_schedule(self):
        """ The shift as dated lines of the roster schedule of the employee. """
        self.ensure_one()
        self._clear_schedule()
        employee = self.employee_id.sudo()
        if not employee.roster_calendar_id:
            employee._start_rostering(self.date)
        lines = self.env['resource.calendar.attendance'].sudo().create([{
            'calendar_id': employee.roster_calendar_id.id,
            'date': self.date + timedelta(days=day),
            'hour_from': hour_from,
            'hour_to': hour_to,
            **({'work_entry_type_id': self.template_id.work_entry_type_id.id}
               if self.template_id.work_entry_type_id else {}),
        } for day, hour_from, hour_to in self._segments()])
        self.sudo().attendance_ids = lines

    def _clear_schedule(self):
        self.sudo().attendance_ids.unlink()

    def _notify(self, subject):
        """ One message per employee, listing their shifts. """
        for employee, shifts in self.grouped('employee_id').items():
            partner = employee.sudo().user_id.partner_id
            if not partner:
                continue
            body = '<br/>'.join(self.env._('%(date)s: %(from)s-%(to)s %(name)s', date=shift.date,
                                           **{'from': format_duration(shift.hour_from)},
                                           to=format_duration(shift.hour_to), name=shift.template_id.name or '')
                                for shift in shifts.sorted('start'))
            employee.sudo().message_notify(partner_ids=partner.ids, subject=subject, body=body,
                                           subtype_xmlid='mail.mt_note')

    def action_unpublish(self):
        self._check_planner()
        published = self.filtered(lambda s: s.state == 'published')
        published._clear_schedule()
        published.write({'state': 'draft'})
        return True

    def write(self, vals):
        timing = {'employee_id', 'date', 'hour_from', 'hour_to', 'break_from', 'break_to', 'template_id'}
        published = self.filtered(lambda s: s.state == 'published') if timing & set(vals) else self.browse()
        old_employees = {shift: shift.employee_id for shift in published}
        result = super().write(vals)
        for shift in published:
            if shift.employee_id:
                shift._write_schedule()
            else:
                shift._clear_schedule()
        changed = published.filtered(lambda s: s.employee_id)
        if changed:
            changed._notify(self.env._('Your shifts changed'))
        for shift, employee in old_employees.items():
            if employee and employee != shift.employee_id:
                shift._notify_removed(employee)
        return result

    def _notify_removed(self, employee):
        partner = employee.sudo().user_id.partner_id
        if partner:
            employee.sudo().message_notify(partner_ids=partner.ids, subject=self.env._('A shift of yours is cancelled'),
                                           body=self.env._('%(date)s: %(from)s-%(to)s', date=self.date,
                                                           **{'from': format_duration(self.hour_from)},
                                                           to=format_duration(self.hour_to)),
                                           subtype_xmlid='mail.mt_note')

    def unlink(self):
        published = self.filtered(lambda s: s.state == 'published' and s.employee_id)
        for shift in published:
            shift._notify_removed(shift.employee_id)
        self._clear_schedule()
        return super().unlink()

    # ------------------------------------------------------------------
    # Roster board
    # ------------------------------------------------------------------

    @api.model
    def _roster_employees(self, date_from, date_to, department_id=False):
        # the planners may not be HR officers: the roster reads the employees of the companies of the user
        domain = [('company_id', 'in', self.env.companies.ids)]
        if department_id:
            domain.append(('department_id', 'child_of', department_id))
        rostered = self.env['hr.employee'].sudo().search(domain + [('roster_calendar_id', '!=', False)])
        planned_domain = [('date', '>=', date_from), ('date', '<=', date_to), ('employee_id', '!=', False)]
        if department_id:
            planned_domain.append(('department_id', 'child_of', department_id))
        planned = self.search(planned_domain).employee_id.sudo()
        return (rostered | planned).sorted(lambda e: (e.department_id.name or '', e.name))

    @api.model
    def roster_data(self, date_from, days=7, department_id=False):
        """ The roster board: the employees, the days, the shifts, the time off and the unavailability. """
        date_from = fields.Date.to_date(date_from)
        date_to = date_from + timedelta(days=days - 1)
        employees = self._roster_employees(date_from, date_to, department_id)
        domain = [('date', '>=', date_from), ('date', '<=', date_to),
                  '|', ('employee_id', 'in', employees.ids), ('employee_id', '=', False)]
        if department_id:
            domain += ['|', ('employee_id', '!=', False), ('department_id', 'child_of', department_id)]
        shifts = self.search(domain)
        warnings = shifts._check()
        dates = [date_from + timedelta(days=index) for index in range(days)]
        off = defaultdict(dict)
        start = datetime.combine(date_from, time.min)
        stop = datetime.combine(date_to + timedelta(days=1), time.min)
        sudo_employees = employees.sudo()
        leaves = self.env['resource.calendar.leaves'].sudo().search([
            ('date_from', '<', stop), ('date_to', '>', start),
            '|', ('resource_id', 'in', sudo_employees.resource_id.ids),
            '&', ('resource_id', '=', False), ('company_id', 'in', sudo_employees.company_id.ids + [False])])
        for employee in sudo_employees:
            for leave in leaves.filtered(
                    lambda time_off: not time_off.resource_id or time_off.resource_id == employee.resource_id):
                for day in dates:
                    if leave.date_from < datetime.combine(day + timedelta(days=1), time.min) and \
                            leave.date_to > datetime.combine(day, time.min):
                        off[employee.id][str(day)] = leave.name or self.env._('Time Off')
        unavailable = self.env['hr.shift.unavailability'].sudo().search([
            ('employee_id', 'in', employees.ids), ('date_from', '<=', date_to), ('date_to', '>=', date_from)])
        busy = defaultdict(dict)
        for unavailability in unavailable:
            for day in dates:
                if unavailability.date_from <= day <= unavailability.date_to:
                    busy[unavailability.employee_id.id][str(day)] = unavailability.reason or self.env._('Unavailable')
        templates = self.env['hr.shift.template'].search([('company_id', 'in', self.env.companies.ids + [False])])
        return {
            'dates': [str(day) for day in dates],
            'employees': [{
                'id': employee.id, 'name': employee.name, 'department': employee.department_id.name or '',
                'hours': sum(shifts.filtered(lambda s: s.employee_id == employee).mapped('hours')),
                'off': off.get(employee.id, {}), 'unavailable': busy.get(employee.id, {}),
            } for employee in employees],
            'shifts': [{
                'id': shift.id, 'employee_id': shift.employee_id.id or False, 'date': str(shift.date),
                'label': shift.template_id.code or '', 'name': shift.template_id.name or '',
                'time': '%s-%s' % (format_duration(shift.hour_from), format_duration(shift.hour_to)),
                'color': shift.template_id.color or 0, 'state': shift.state,
                'warning': '\n'.join(warnings.get(shift.id, [])),
            } for shift in shifts],
            'templates': [{'id': template.id, 'code': template.code, 'name': template.display_name,
                           'color': template.color} for template in templates],
            'can_edit': self.env.user.has_group('om_hr_shift.group_shift_planner'),
        }

    @api.model
    def roster_assign(self, employee_id, date, template_id, department_id=False):
        self._check_planner()
        template = self.env['hr.shift.template'].browse(template_id)
        shift = self.create(dict(template._shift_values(), employee_id=employee_id or False,
                                 date=fields.Date.to_date(date),
                                 **({'department_id': department_id} if not employee_id and department_id else {})))
        return shift.id

    @api.model
    def roster_move(self, shift_id, employee_id, date):
        self._check_planner()
        self.browse(shift_id).write({'employee_id': employee_id or False, 'date': fields.Date.to_date(date)})
        return True

    @api.model
    def roster_copy_previous(self, date_from, days=7, department_id=False):
        """ The draft shifts of the period before, on the same days of this one, for the employees with no shift on
            the day yet. """
        self._check_planner()
        date_from = fields.Date.to_date(date_from)
        source_from = date_from - timedelta(days=days)
        domain = [('date', '>=', source_from), ('date', '<', date_from)]
        if department_id:
            domain.append(('department_id', 'child_of', department_id))
        sources = self.search(domain)
        existing = {(shift.employee_id.id, shift.date) for shift in self.search(
            [('date', '>=', date_from), ('date', '<', date_from + timedelta(days=days)), ('employee_id', '!=', False)])}
        values = []
        for shift in sources:
            day = shift.date + timedelta(days=days)
            if shift.employee_id and (shift.employee_id.id, day) in existing:
                continue
            values.append({'employee_id': shift.employee_id.id or False, 'date': day,
                           'template_id': shift.template_id.id, 'department_id': shift.department_id.id,
                           'hour_from': shift.hour_from, 'hour_to': shift.hour_to,
                           'break_from': shift.break_from, 'break_to': shift.break_to, 'note': shift.note})
        return len(self.create(values))

    @api.model
    def roster_publish(self, date_from, days=7, department_id=False):
        date_from = fields.Date.to_date(date_from)
        domain = [('date', '>=', date_from), ('date', '<', date_from + timedelta(days=days)), ('state', '=', 'draft')]
        if department_id:
            domain.append(('department_id', 'child_of', department_id))
        shifts = self.search(domain)
        if not shifts:
            raise UserError(self.env._('No draft shift to publish in these days.'))
        return shifts.action_publish()
