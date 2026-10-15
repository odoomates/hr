from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    om_shift_min_rest = fields.Float(string='Minimum Rest Between Shifts', default=11.0,
                                     help='Hours between the end of a shift and the start of the next one.')
    om_shift_max_week_hours = fields.Float(string='Maximum Hours per Week', default=48.0,
                                           help='Hours of shifts in a week, Monday to Sunday.')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    om_shift_min_rest = fields.Float(related='company_id.om_shift_min_rest', readonly=False)
    om_shift_max_week_hours = fields.Float(related='company_id.om_shift_max_week_hours', readonly=False)
