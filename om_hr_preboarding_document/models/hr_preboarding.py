from odoo import api, fields, models


class HrPreboardingStep(models.Model):
    _inherit = 'hr.preboarding.step'

    kind = fields.Selection(selection_add=[('document', 'Upload a Document')], ondelete={'document': 'cascade'})
    document_type_id = fields.Many2one(
        'document.type', domain=[('res_model', '=', 'hr.employee')],
        help='The document the new hire uploads, e.g. Passport. The step is done once a file is uploaded.')

    @api.model
    def _auto_kinds(self):
        return super()._auto_kinds() + ['document']

    def _line_values(self):
        return dict(super()._line_values(), document_type_id=self.document_type_id.id)


class HrPreboardingLine(models.Model):
    _inherit = 'hr.preboarding.line'

    document_type_id = fields.Many2one('document.type')
    document_id = fields.Many2one('document.document')

    def _on_started(self):
        """ The document to upload waits in the documents of the employee, as HR would ask for it. """
        result = super()._on_started()
        Document = self.env['document.document'].sudo()
        for line in self.filtered(lambda line: line.kind == 'document' and line.document_type_id):
            employee = line.employee_id
            document = Document.search([('res_model', '=', 'hr.employee'), ('res_id', '=', employee.id),
                                        ('type_id', '=', line.document_type_id.id)], limit=1)
            line.sudo().document_id = document or Document.create({
                'res_model': 'hr.employee', 'res_id': employee.id, 'type_id': line.document_type_id.id})
        return result

    def _refresh(self):
        result = super()._refresh()
        for line in self.filtered(lambda line: line.kind == 'document' and line.state != 'done'):
            if line.document_id.sudo().attachment_ids:
                line._mark_done()
        return result
