from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrBiometricReprocess(models.TransientModel):
    """ Process the punches of a period again, e.g. after a change of mode or late punches. """
    _name = 'hr.biometric.reprocess'
    _description = 'Process Biometric Punches Again'

    date_from = fields.Date(string='From', required=True, default=fields.Date.today)
    date_to = fields.Date(string='To', required=True, default=fields.Date.today)
    device_ids = fields.Many2many('hr.biometric.device', string='Devices', help='Empty: all the devices.')
    employee_ids = fields.Many2many('hr.employee', string='Employees', help='Empty: all the employees.')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(wizard.date_to < wizard.date_from for wizard in self):
            raise UserError(_('The period ends after it starts.'))

    def action_reprocess(self):
        logs = self.env['hr.biometric.log']._reprocess(self.date_from, self.date_to, self.device_ids,
                                                        self.employee_ids)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Processed Punches'),
            'res_model': 'hr.biometric.log',
            'view_mode': 'list,form',
            'domain': [('id', 'in', logs.ids)],
        }
