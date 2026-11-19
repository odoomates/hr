from odoo import fields, models


class HrBiometricLog(models.Model):
    _inherit = 'hr.biometric.log'

    source = fields.Selection(selection_add=[('zk', 'TCP')], ondelete={'zk': 'set default'})
