from odoo import fields, models


class OmHrLatenessExcuse(models.TransientModel):
    _name = 'om.hr.lateness.excuse'
    _description = 'Excuse a Lateness'

    lateness_ids = fields.Many2many('om.hr.lateness', string='Lateness', required=True)
    reason = fields.Char(required=True, help='e.g. an errand for the company, a traffic accident')

    def action_excuse(self):
        self.ensure_one()
        return self.lateness_ids._om_excuse(self.reason)
