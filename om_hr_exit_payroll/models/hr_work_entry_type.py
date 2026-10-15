from odoo import fields, models


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    om_encashable = fields.Boolean(
        string='Paid Out at the Exit',
        help='The days of this time off the employee has not taken are paid in his final settlement.')
