from odoo import api, models


class SignRole(models.Model):
    _inherit = 'sign.role'

    @api.model
    def _partners_models(self):
        return super()._partners_models() + ('hr.employee',)

    @api.model
    def _as_partners(self, records):
        if records._name == 'hr.employee':
            return records.work_contact_id
        return super()._as_partners(records)
