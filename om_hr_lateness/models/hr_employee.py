from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    lateness_policy_id = fields.Many2one('hr.lateness.policy',
                                            help='The policy of the employees with none of their own.')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lateness_policy_id = fields.Many2one(related='company_id.lateness_policy_id', readonly=False)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    lateness_policy_id = fields.Many2one(
        'hr.lateness.policy', groups='hr.group_hr_user',
        help='Leave empty for the policy of the company.', check_company=True)

    @api.model
    def _company_checked_fields(self):
        return super()._company_checked_fields() + ['lateness_policy_id']

    def _lateness_policy(self):
        self.ensure_one()
        employee = self.sudo()
        return employee.lateness_policy_id or employee.company_id.lateness_policy_id or \
            self.env['hr.lateness.policy'].sudo().search(
                [('company_id', 'in', [employee.company_id.id, False])], order='company_id, id', limit=1)

    def _schedule_of_day(self, day, intervals, tz):
        """ :return: the start and the end of the work of `day`, the end running past midnight for a night shift;
            None on a day off, on time off or on a public holiday """
        day_start = datetime.combine(day, time.min, tz)
        next_day = day_start + timedelta(days=1)
        blocks = sorted((start, stop) for start, stop, _meta in intervals if day_start <= start < next_day)
        if not blocks:
            return None
        start, stop = blocks[0][0], blocks[-1][1]
        for later_start, later_stop in sorted((s, e) for s, e, _meta in intervals if s >= next_day):
            # the calendar ends a day at 23:59:59.999999
            if later_start - stop > timedelta(seconds=1):
                break
            stop = later_stop
        return start, stop

    def _compute_lateness(self, date_from, date_to):
        """ Record the late arrivals and the early departures of the employees between the two days. """
        Lateness = self.env['hr.lateness'].sudo()
        to_evaluate = Lateness
        for employee in self.sudo():
            existing = Lateness.search([('employee_id', '=', employee.id), ('date', '>=', date_from),
                                        ('date', '<=', date_to)])
            policy = employee._lateness_policy()
            calendar = employee.resource_calendar_id
            found = {}
            if policy and calendar and not calendar._is_flexible():
                found = employee._find_lateness(policy, date_from, date_to)
            done = Lateness
            for (day, kind), values in found.items():
                lateness = existing.filtered(lambda entry: entry.date == day and entry.kind == kind)
                values = dict(values, policy_id=policy.id)
                if lateness:
                    lateness.write(values)
                else:
                    lateness = Lateness.create(dict(values, employee_id=employee.id, date=day, kind=kind))
                done |= lateness
            gone = existing - done
            to_evaluate |= done | gone
            months = {(employee, lateness.date.replace(day=1)) for lateness in to_evaluate if lateness.exists()}
            gone.unlink()
            for month_employee, month in months | {(employee, day.replace(day=1)) for day, _kind in found}:
                Lateness._evaluate(month_employee, month)
        return True

    def _expected_intervals(self, start, end):
        """ :return: the work intervals of the employee, time off and public holidays left out """
        self.ensure_one()
        if self._get_versions_with_contract_overlap_with_period(start.date(), end.date()):
            return self._get_expected_attendances(start, end)
        # without a contract, the schedule of the employee, read the same way
        return self.resource_calendar_id._work_intervals_batch(
            start, end, resources_per_tz=self._get_resources_per_tz(start),
            domain=[('company_id', 'in', [False, self.company_id.id]), ('count_as', '=', 'absence')],
        )[self.resource_id.id]

    def _find_lateness(self, policy, date_from, date_to):
        """ :return: {(day, kind): values} of the latenesses beyond the grace minutes of the policy """
        self.ensure_one()
        tz = ZoneInfo(self._get_tz(date=date_from))
        intervals = self._expected_intervals(
            datetime.combine(date_from, time.min, tz), datetime.combine(date_to + timedelta(days=2), time.min, tz))
        attendances = self.env['hr.attendance'].sudo().search([
            ('employee_id', '=', self.id), ('date', '>=', date_from), ('date', '<=', date_to),
            ('source_attendance_id', '=', False)])
        found = {}
        for day in sorted(set(attendances.mapped('date'))):
            schedule = self._schedule_of_day(day, intervals, tz)
            if not schedule:
                continue
            scheduled_in, scheduled_out = schedule
            of_day = attendances.filtered(lambda attendance: attendance.date == day)
            first = of_day.sorted('check_in')[0]
            check_in = first.check_in.replace(tzinfo=UTC)
            late = int((check_in - scheduled_in).total_seconds() // 60)
            if late > policy.grace_in:
                found[(day, 'late_in')] = {
                    'scheduled_at': scheduled_in.astimezone(UTC).replace(tzinfo=None),
                    'actual_at': first.check_in, 'minutes': late, 'attendance_id': first.id}
            if policy.early_out and all(of_day.mapped('check_out')):
                last = of_day.sorted('check_out')[-1]
                check_out = last.check_out.replace(tzinfo=UTC)
                early = int((scheduled_out - check_out).total_seconds() // 60)
                if early > policy.grace_out:
                    found[(day, 'early_out')] = {
                        'scheduled_at': scheduled_out.astimezone(UTC).replace(tzinfo=None),
                        'actual_at': last.check_out, 'minutes': early, 'attendance_id': last.id}
        return found

    @api.model
    def _cron_compute_lateness(self, days=7):
        """ The last days again, for the schedules, the time off and the attendances changed since. """
        today = fields.Date.context_today(self)
        date_from = today - timedelta(days=days)
        employees = self.env['hr.attendance'].sudo().search(
            [('date', '>=', date_from), ('date', '<', today)]).employee_id
        employees._compute_lateness(date_from, today - timedelta(days=1))
