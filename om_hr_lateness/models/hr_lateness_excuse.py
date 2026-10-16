from odoo import fields, models


class HrLatenessExcuse(models.TransientModel):
    _name = 'hr.lateness.excuse'
    _description = 'Excuse a Lateness'

    lateness_ids = fields.Many2many('hr.lateness', string='Lateness', required=True)
    reason = fields.Char(required=True, help='e.g. an errand for the company, a traffic accident')

    def action_excuse(self):
        self.ensure_one()
        return self.lateness_ids._excuse(self.reason)
