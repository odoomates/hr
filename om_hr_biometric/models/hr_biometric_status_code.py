from odoo import api, fields, models
from odoo.exceptions import ValidationError

ACTIONS = [
    ('check_in', 'Check In'),
    ('check_out', 'Check Out'),
    ('break_out', 'Break Out'),
    ('break_in', 'Break In'),
    ('overtime_in', 'Overtime In'),
    ('overtime_out', 'Overtime Out'),
    ('ignore', 'Ignore'),
]
DIRECTIONS = {'check_in': 'in', 'break_in': 'in', 'overtime_in': 'in',
              'check_out': 'out', 'break_out': 'out', 'overtime_out': 'out', 'ignore': 'ignore'}


class HrBiometricStatusCode(models.Model):
    """ What the status the employee selects on the device means, for the devices in Status Codes mode. """
    _name = 'hr.biometric.status.code'
    _description = 'Biometric Status Code'
    _order = 'device_id, code'

    device_id = fields.Many2one('hr.biometric.device', required=True, ondelete='cascade', index=True)
    code = fields.Char(required=True)
    action = fields.Selection(ACTIONS, required=True, default='check_in')

    _code_uniq = models.Constraint('UNIQUE(device_id, code)', 'A status code is defined once per device.')

    @api.constrains('code')
    def _check_code(self):
        for status in self:
            if not status.code.strip():
                raise ValidationError(self.env._('A status code cannot be empty.'))

    def _direction(self):
        """ :return: 'in', 'out' or 'ignore' """
        self.ensure_one()
        return DIRECTIONS[self.action]
