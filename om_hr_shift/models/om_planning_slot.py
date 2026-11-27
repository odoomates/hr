from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.intervals import Intervals

from .om_planning_template import shift_segments
from .shift_migration import migrate_legacy

# the changes of a published slot written again on the roster schedule of its employees
ROSTER_FIELDS = {'start_datetime', 'end_datetime', 'resource_ids', 'break_hours', 'break_from', 'template_id',
                 'state', 'source_ref'}


class OmPlanningSlot(models.Model):
    """ A shift is a slot of an employee, or an open slot no one works yet. Published, it is written on the roster
    schedule of the employee, which the time off, the work entries, the overtime and the payroll all read. """
    _inherit = 'om.planning.slot'

    employee_id = fields.Many2one('hr.employee', compute='_compute_employee_id', store=True, index='btree_not_null',
                                  help='The first employee of the slot.')
    template_id = fields.Many2one(check_company=True)
    # an open shift keeps the department it is planned for: the employees of that department claim it
    department_id = fields.Many2one(readonly=False)
    shift_date = fields.Date(compute='_compute_shift_date', store=True, index=True, string='Day',
                             help='The day the shift starts, in the timezone of its employee.')
    break_from = fields.Float(help='The hour the unpaid break starts; outside the shift, the break is in its middle.')
    roster_attendance_ids = fields.Many2many(
        'resource.calendar.attendance', 'om_planning_slot_roster_attendance_rel', 'slot_id', 'attendance_id',
        string='Schedule Lines', copy=False, readonly=True)
    old_shift_id = fields.Integer(string='Former Shift', readonly=True, copy=False, index='btree_not_null')

    @api.depends('resource_ids.employee_id')
    def _compute_employee_id(self):
        for slot in self:
            slot.employee_id = slot.resource_ids._origin.sudo().employee_id[:1]

    @api.depends('resource_ids.employee_id.department_id')
    def _compute_department_id(self):
        for slot in self:
            employees = slot.resource_ids._origin.sudo().employee_id
            slot.department_id = employees[:1].department_id if employees else slot.department_id

    @api.depends('start_datetime', 'resource_ids.tz', 'company_id')
    def _compute_shift_date(self):
        for slot in self:
            slot.shift_date = slot.start_datetime and slot._shift_local(slot.start_datetime).date()

    @api.depends('template_id')
    def _compute_display_name(self):
        result = super()._compute_display_name()
        # a shift without title nor role is named after its template
        if self.env.context.get('om_planning_label') == 'role':
            for slot in self.filtered(lambda s: s.template_id and not s.name and not s.role_id):
                slot.display_name = slot.template_id.name
        return result

    def _shift_tz(self, resource=None):
        self.ensure_one()
        resource = resource or self.resource_ids._origin.filtered(lambda r: r.resource_type == 'user')[:1]
        return ZoneInfo(resource.tz or self.company_id.partner_id.tz or self.env.context.get('tz')
                        or self.env.user.tz or 'UTC')

    def _shift_local(self, moment, resource=None):
        return moment.replace(tzinfo=UTC).astimezone(self._shift_tz(resource)).replace(tzinfo=None)

    def _shift_segments(self, resource=None):
        """ :return: the worked parts of the shift in the timezone of `resource`, see `shift_segments` """
        self.ensure_one()
        return shift_segments(self._shift_local(self.start_datetime, resource),
                              self._shift_local(self.end_datetime, resource), self.break_from, self.break_hours)

    # ------------------------------------------------------------------
    # Roster schedule
    # ------------------------------------------------------------------

    def _shift_on_roster(self):
        """ The published shifts are the working schedule; a slot planned for a document (an order, a task...) is
            work within that schedule. """
        self.ensure_one()
        return self.state == 'published' and not self.source_ref

    def _shift_sync_roster(self):
        """ The published shifts as dated lines of the roster schedule of their employees. """
        if self.env.context.get('om_hr_shift_no_roster'):
            return
        Attendance = self.env['resource.calendar.attendance'].sudo()
        for slot in self:
            slot.sudo().roster_attendance_ids.unlink()
            if not slot._shift_on_roster():
                continue
            values = []
            for resource in slot.resource_ids._origin.sudo().filtered('employee_id'):
                employee = resource.employee_id[:1]
                segments = slot._shift_segments(resource)
                if not segments:
                    continue
                if not employee.roster_calendar_id:
                    employee._start_rostering(segments[0][0])
                values += [{
                    'calendar_id': employee.roster_calendar_id.id,
                    'date': day,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    **({'work_entry_type_id': slot.template_id.work_entry_type_id.id}
                       if slot.template_id.work_entry_type_id else {}),
                } for day, hour_from, hour_to in segments]
            slot.sudo().roster_attendance_ids = Attendance.create(values)

    @api.model_create_multi
    def create(self, vals_list):
        slots = super().create(vals_list)
        slots.filtered(lambda slot: slot.state == 'published')._shift_sync_roster()
        return slots

    def write(self, vals):
        result = super().write(vals)
        if ROSTER_FIELDS & set(vals):
            self._shift_sync_roster()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_shift_roster(self):
        self.sudo().roster_attendance_ids.unlink()

    @api.model
    def _shift_migrate_legacy(self):
        """ Run on each update of the module, before its data: the shifts of the former versions move to the
            planning. """
        migrate_legacy(self.sudo().env)

    def _check_shift_planner(self):
        if not self.env.user.has_group('om_hr_shift.group_shift_planner'):
            raise UserError(self.env._('Only the shift planners publish and change the shifts.'))

    # ------------------------------------------------------------------
    # Conflicts and Gantt
    # ------------------------------------------------------------------

    def _shift_rostered_resources(self, resources):
        return resources.sudo().filtered(lambda r: r.employee_id[:1].roster_calendar_id)

    def _planning_check(self):
        """ A rostered employee works their shifts: a shift is never outside their working schedule. """
        result = super()._planning_check()
        rostered = self._shift_rostered_resources(self.resource_ids._origin).ids
        if rostered:
            for slot_id, problems in result.items():
                result[slot_id] = [problem for problem in problems
                                   if not (problem['type'] == 'outside' and problem['resource_id'] in rostered)]
        return result

    @api.model
    def gantt_unavailability(self, start_date, end_date, scale, group_bys=None, rows=None):
        """ The days of a rostered employee are free until planned: only their time off and unavailability are
            greyed. """
        rows = super().gantt_unavailability(start_date, end_date, scale, group_bys=group_bys, rows=rows)
        resource_ids = set()

        def collect(row_list):
            for row in row_list or []:
                if row.get('groupedBy') and row['groupedBy'][-1] == 'resource_ids' and row.get('resId'):
                    resource_ids.add(row['resId'])
                collect(row.get('rows'))

        collect(rows)
        rostered = self._shift_rostered_resources(self.env['resource.resource'].browse(sorted(resource_ids)).exists())
        if not rostered:
            return rows
        full = Intervals([(rostered._planning_utc(start_date), rostered._planning_utc(end_date),
                           self.env['om.planning.slot'])])
        leaves = rostered._planning_leave_intervals(start_date, end_date)
        unavailable = {
            resource.id: [
                {'start': start.astimezone(UTC).replace(tzinfo=None), 'stop': stop.astimezone(UTC).replace(tzinfo=None)}
                for start, stop, _records in leaves.get(resource.id, Intervals()) & full
            ]
            for resource in rostered
        }

        def fill(row_list):
            for row in row_list or []:
                if row.get('groupedBy') and row['groupedBy'][-1] == 'resource_ids' and row.get('resId') in unavailable:
                    row['unavailabilities'] = unavailable[row['resId']]
                fill(row.get('rows'))

        fill(rows)
        return rows

    # ------------------------------------------------------------------
    # Demo data
    # ------------------------------------------------------------------

    @api.model
    def _shift_demo(self):
        """ Two rostered developers: this week published, next week in draft; an open shift next week to claim,
            a claim waiting for its approval and a swap waiting for the colleague. """
        ref = self.env.ref
        stw, jog, niv = ref('hr.employee_stw'), ref('hr.employee_jog'), ref('hr.employee_niv')
        morning, evening = ref('om_hr_shift.template_morning'), ref('om_hr_shift.template_evening')
        today = fields.Date.context_today(self)
        monday = today - relativedelta(days=today.weekday())
        next_monday = monday + relativedelta(weeks=1)
        plan = [(stw, morning, monday, 0), (stw, morning, monday, 1), (stw, morning, monday, 2),
                (jog, evening, monday, 0), (jog, evening, monday, 2), (jog, evening, monday, 3),
                (stw, morning, next_monday, 0), (jog, evening, next_monday, 0),
                (self.env['hr.employee'], morning, next_monday, 3)]
        names = ['stw_mon', 'stw_tue', 'stw_wed', 'jog_mon', 'jog_wed', 'jog_thu', 'stw_next_mon', 'jog_next_mon',
                 'open']
        slots = self.create([template._shift_values(week + relativedelta(days=day), employee)
                             for employee, template, week, day in plan])
        slots[-1].note = self.env._('Cover for the stock count.')
        (slots[:6] | slots[-1]).action_publish()
        self.env['ir.model.data']._update_xmlids([
            {'xml_id': 'om_hr_shift.demo_shift_%s' % name, 'record': slot, 'noupdate': True}
            for name, slot in zip(names, slots, strict=True)])
        tz = ZoneInfo(stw.resource_id.tz or 'UTC')
        unavailable = datetime.combine(next_monday + relativedelta(days=4), time.min, tzinfo=tz)
        leave = self.env['resource.calendar.leaves'].create({
            'name': self.env._('Medical appointment'), 'resource_id': stw.resource_id.id,
            'date_from': unavailable.astimezone(UTC).replace(tzinfo=None),
            'date_to': (unavailable + relativedelta(hours=23, minutes=59)).astimezone(UTC).replace(tzinfo=None),
            'shift_unavailability': True})
        Request = self.env['om.planning.request']
        claim = Request.create({'request_type': 'claim', 'slot_id': slots[-1].id, 'resource_id': niv.resource_id.id,
                                'reason': self.env._('I can take it.')})
        swap = Request.create({'slot_id': slots[4].id, 'target_slot_id': slots[2].id,
                               'resource_id': jog.resource_id.id,
                               'reason': self.env._('A family dinner on Wednesday evening.')})
        self.env['ir.model.data']._update_xmlids([
            {'xml_id': 'om_hr_shift.demo_unavailability_stw', 'record': leave, 'noupdate': True},
            {'xml_id': 'om_hr_shift.demo_request_claim', 'record': claim, 'noupdate': True},
            {'xml_id': 'om_hr_shift.demo_request_swap', 'record': swap, 'noupdate': True},
        ])
