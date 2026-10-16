from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    preboarding_from_offer = fields.Boolean(
        string='Start From Accepted Offers',
        help='Start the pre-boarding of the employee created from an accepted job offer, on its start date.')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    preboarding_from_offer = fields.Boolean(related='company_id.preboarding_from_offer', readonly=False)
