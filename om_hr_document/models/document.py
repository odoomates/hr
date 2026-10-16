from odoo import api, fields, models

# the core fields of the employee holding the number of a document type, by type code
EMPLOYEE_NUMBER_FIELDS = {
    'NATIONAL_ID': 'identification_id',
    'PASSPORT': 'passport_id',
}


class Document(models.Model):
    _inherit = 'document.document'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', compute='_compute_employee_id', store=True, index='btree_not_null',
        ondelete='cascade')
    department_id = fields.Many2one(related='employee_id.department_id', store=True, string='Department')

    @api.depends('res_model', 'res_id')
    def _compute_employee_id(self):
        for document in self:
            document.employee_id = document.res_id if document.res_model == 'hr.employee' else False

    @api.model_create_multi
    def create(self, vals_list):
        documents = super().create(vals_list)
        documents._hr_sync_employee_numbers()
        return documents

    def write(self, vals):
        result = super().write(vals)
        if {'number', 'type_id', 'active'} & set(vals):
            self._hr_sync_employee_numbers()
        return result

    def _hr_sync_employee_numbers(self):
        """ The number of a National ID or a passport is also set on the employee, where core HR shows it. """
        for document in self.filtered(lambda d: d.active and d.employee_id and d.number):
            field = EMPLOYEE_NUMBER_FIELDS.get(document.type_id.code)
            if field and document.employee_id.sudo()[field] != document.number:
                document.employee_id.sudo()[field] = document.number
