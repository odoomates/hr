from odoo import fields, models

from ..models.hr_biometric_template import FINGERS


class HrBiometricEnroll(models.TransientModel):
    """ Start the enrollment of a finger on the device: the employee then places it on the device. """
    _name = 'hr.biometric.enroll'
    _description = 'Enroll a Fingerprint'

    device_user_id = fields.Many2one('hr.biometric.device.user', string='User', required=True)
    finger = fields.Selection([(str(index), name) for index, name in FINGERS], required=True, default='6')

    def action_enroll(self):
        device = self.device_user_id.device_id
        device._enroll(self.device_user_id, int(self.finger))
        return device._notify(self.env._('%(user)s places the finger on %(device)s three times.',
                                         user=self.device_user_id.display_name, device=device.name))
