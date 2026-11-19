from datetime import datetime, time, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class HrBiometricDownload(models.TransientModel):
    """ Ask devices for their punches of a period, e.g. after they were offline. """
    _name = 'hr.biometric.download'
    _description = 'Download Biometric Punches'

    device_ids = fields.Many2many('hr.biometric.device', string='Devices', required=True)
    date_from = fields.Datetime(string='From', required=True,
                                default=lambda self: datetime.combine(fields.Date.today() - timedelta(days=7),
                                                                      time.min))
    date_to = fields.Datetime(string='To', required=True, default=fields.Datetime.now)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(wizard.date_to < wizard.date_from for wizard in self):
            raise UserError(self.env._('The period ends after it starts.'))

    def action_download(self):
        self.device_ids._query_logs(self.date_from, self.date_to)
        return self.device_ids._notify(self.env._('The devices send their punches at their next contact.'))
