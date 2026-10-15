from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    om_hr_exit_notice_days = fields.Integer(
        string='Notice Period (Days)', default=30,
        help='Proposed between the notice and the last working day of an exit.')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    om_hr_exit_notice_days = fields.Integer(related='company_id.om_hr_exit_notice_days', readonly=False)
