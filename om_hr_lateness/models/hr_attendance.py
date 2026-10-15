from odoo import api, models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    def _om_lateness_days(self):
        return {(attendance.employee_id, attendance.date) for attendance in self.sudo()
                if not attendance.source_attendance_id and attendance.date}

    @staticmethod
    def _om_refresh_lateness(days):
        for employee, day in days:
            if employee.exists():
                employee._om_compute_lateness(day, day)

    @api.model_create_multi
    def create(self, vals_list):
        attendances = super().create(vals_list)
        self._om_refresh_lateness(attendances._om_lateness_days())
        return attendances

    def write(self, vals):
        if not {'check_in', 'check_out', 'employee_id'} & set(vals):
            return super().write(vals)
        before = self._om_lateness_days()
        result = super().write(vals)
        self._om_refresh_lateness(before | self._om_lateness_days())
        return result

    def unlink(self):
        days = self._om_lateness_days()
        result = super().unlink()
        self._om_refresh_lateness(days)
        return result
