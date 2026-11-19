from datetime import timedelta

from odoo import models

# a punch belongs to a shift from this long before its start to this long after its end
MARGIN = timedelta(hours=4)


class HrBiometricLog(models.Model):
    _inherit = 'hr.biometric.log'

    def _shift(self):
        """ :return: the published shift of the employee the punch belongs to, the nearest one """
        self.ensure_one()
        shifts = self.env['hr.shift'].sudo().search([
            ('employee_id', '=', self.employee_id.id), ('state', '=', 'published'),
            ('start', '<=', self.timestamp + MARGIN), ('stop', '>=', self.timestamp - MARGIN),
        ])
        return min(shifts, key=lambda shift: min(abs(self.timestamp - shift.start), abs(self.timestamp - shift.stop)),
                   default=shifts)

    def _near_start(self, shift):
        return abs(self.timestamp - shift.start) <= abs(self.timestamp - shift.stop)

    def _is_forgotten(self, attendance):
        """ An attendance opened before the shift of this punch, punched near its start, was never checked out. """
        shift = self._shift()
        if shift and attendance.check_in < shift.start - MARGIN and self._near_start(shift):
            return True
        return super()._is_forgotten(attendance)

    def _toggle(self, last, open_ok):
        """ A punch near the end of a shift checks out, even when the check-in was missed. """
        shift = self._shift()
        if shift and not open_ok:
            return 'in' if self._near_start(shift) else 'out'
        return super()._toggle(last, open_ok)
