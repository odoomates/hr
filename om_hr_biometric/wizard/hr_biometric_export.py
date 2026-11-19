from odoo import _, fields, models
from odoo.exceptions import UserError


class HrBiometricExport(models.TransientModel):
    """ Enroll employees on devices, or update their name there. """
    _name = 'hr.biometric.export'
    _description = 'Send Employees to Biometric Devices'

    device_ids = fields.Many2many('hr.biometric.device', string='Devices', required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)

    def action_export(self):
        others = self.employee_ids.filtered(lambda e: e.company_id not in self.device_ids.company_id)
        if others:
            raise UserError(_('No device of the company of %s is selected.', ', '.join(others.mapped('name'))))
        self.device_ids._push_users(self.employee_ids)
        return self.device_ids._notify(_('The employees are sent at the next contact of the devices.'))
