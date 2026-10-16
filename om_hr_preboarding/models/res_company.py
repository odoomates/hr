from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    preboarding_welcome = fields.Html(
        string='First Day Information', translate=True, sanitize_style=True,
        default=lambda self: self.env._('<p>Welcome! On your first day, come to the reception at 9:00: your buddy '
                                        'meets you there.</p>'),
        help='Shown to each new hire on their pre-boarding page; it can be changed for each of them.')
    preboarding_plan_id = fields.Many2one(
        'mail.activity.plan', string='Onboarding Plan', domain=[('res_model', '=', 'hr.employee')],
        help='Launched on the employee when their pre-boarding starts, e.g. to prepare their laptop.')
