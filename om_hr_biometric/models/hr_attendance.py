from odoo import fields, models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    in_mode = fields.Selection(selection_add=[('biometric', 'Biometric Device')],
                               ondelete={'biometric': 'set default'})
    out_mode = fields.Selection(selection_add=[('biometric', 'Biometric Device')],
                                ondelete={'biometric': 'set default'})
    in_device_id = fields.Many2one('hr.biometric.device', string='Check-In Device', readonly=True,
                                   index='btree_not_null')
    out_device_id = fields.Many2one('hr.biometric.device', string='Check-Out Device', readonly=True)
    biometric_review = fields.Boolean(string='To Review', copy=False,
                                      help='No check-out was punched: the attendance was closed at its check-in.')

    def action_biometric_reviewed(self):
        self.biometric_review = False
