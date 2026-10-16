from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    preboarding_welcome = fields.Html(related='company_id.preboarding_welcome', readonly=False)
    preboarding_plan_id = fields.Many2one(related='company_id.preboarding_plan_id', readonly=False)
