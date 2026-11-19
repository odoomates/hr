from odoo import fields, models


class HrBiometricCopy(models.TransientModel):
    """ Enroll a device user on other devices with its fingerprints: the employee does not enroll again. """
    _name = 'hr.biometric.copy'
    _description = 'Copy a Biometric User to Other Devices'

    device_user_id = fields.Many2one('hr.biometric.device.user', string='User', required=True)
    source_device_id = fields.Many2one(related='device_user_id.device_id', string='From')
    company_id = fields.Many2one(related='device_user_id.company_id')
    device_ids = fields.Many2many('hr.biometric.device', string='To', required=True,
                                  domain="[('id', '!=', source_device_id), ('company_id', '=', company_id)]")

    def action_copy(self):
        self.device_user_id._copy_to(self.device_ids)
        return self.device_ids._notify(self.env._('%s is copied to the devices.', self.device_user_id.display_name))
