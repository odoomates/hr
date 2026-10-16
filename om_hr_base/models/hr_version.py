from odoo import api, fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    type_id = fields.Many2one('hr.employee.type', string="Employee Category",
                              required=True, help="Employee category",
                              default=lambda self: self.env['hr.employee.type'].search([], limit=1), check_company=True)

    @api.model
    def _company_checked_fields(self):
        """ Hook: :return: the names of the fields added by the HR modules whose company is checked on create and
            write, the model not checking its companies by itself """
        return ['type_id']

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
