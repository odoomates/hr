from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    biometric_max_shift = fields.Float(
        string='Maximum Shift (Hours)', default=16.0,
        help='A check-in still open for longer than this is a forgotten check-out: the next punch starts a new '
             'attendance.')
    biometric_store_templates = fields.Boolean(
        string='Keep Biometric Templates',
        help='Keep the fingerprint and face templates the devices send, to copy the employees to other devices. '
             'They are biometric data: only the attendance managers see them.')
