from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    biometric_max_shift = fields.Float(related='company_id.biometric_max_shift', readonly=False)
    biometric_store_templates = fields.Boolean(related='company_id.biometric_store_templates', readonly=False)
    biometric_tolerance = fields.Integer(related='company_id.biometric_tolerance', readonly=False)
    biometric_offline_minutes = fields.Integer(related='company_id.biometric_offline_minutes', readonly=False)
    biometric_template_count = fields.Integer(compute='_compute_biometric_template_count')

    def _compute_biometric_template_count(self):
        for settings in self:
            settings.biometric_template_count = self.env['hr.biometric.template'].sudo().search_count(
                [('company_id', '=', settings.company_id.id)])

    def action_biometric_purge_templates(self):
        """ Delete the biometric templates of the company kept in Odoo (never those on the devices). """
        self.env['hr.biometric.template'].search([('company_id', '=', self.company_id.id)]).unlink()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
