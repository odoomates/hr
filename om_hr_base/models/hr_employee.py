from odoo import api, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _company_checked_fields(self):
        """ Hook: :return: the names of the fields added by the HR modules whose company is checked on create and
            write, the model not checking its companies by itself """
        return []

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if fnames := self._company_checked_fields():
            records._check_company(fnames)
        return records

    def write(self, vals):
        result = super().write(vals)
        fnames = self._company_checked_fields()
        if fnames and (set(fnames) | {'company_id'}) & set(vals):
            self._check_company(fnames)
        return result
