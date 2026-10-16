from odoo import _, api, fields, models


class OmDocumentMixin(models.AbstractModel):
    """ A record keeping documents, e.g. an employee with a passport and a work permit.

    A model inheriting the mixin names who is reminded of the expiring documents in
    ``_document_responsible_users`` and who holds them in ``_document_holder_partner``.
    """
    _name = 'om.document.mixin'
    _description = 'Document Mixin'

    om_document_ids = fields.One2many(
        'om.document', 'res_id', string='Documents',
        domain=lambda self: [('res_model', '=', self._name)])
    om_document_count = fields.Integer(string='Document Count', compute='_compute_om_document_count')
    om_document_alert_count = fields.Integer(string='Documents to Renew', compute='_compute_om_document_count',
                                             help='The documents expiring or expired.')

    @api.depends('om_document_ids')
    def _compute_om_document_count(self):
        Document = self.env['om.document']
        domain = [('res_model', '=', self._name), ('res_id', 'in', self.ids)]
        counts = dict(Document._read_group(domain, ['res_id'], ['__count']))
        alerts = dict(Document._read_group(
            domain + [('state', 'in', ['expiring', 'expired'])], ['res_id'], ['__count']))
        for record in self:
            record.om_document_count = counts.get(record.id, 0)
            record.om_document_alert_count = alerts.get(record.id, 0)

    def _document_responsible_users(self):
        """ :return: the users reminded of the documents of the record, empty for the users of the type """
        return self.env['res.users']

    def _document_holder_partner(self):
        """ :return: the partner holding the documents of the record, emailed when the type notifies the holder """
        return self.env['res.partner']

    def action_open_om_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documents of %s', self.display_name),
            'res_model': 'om.document',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'search_default_group_type': 0,
            },
        }

    def unlink(self):
        documents = self.env['om.document'].sudo().with_context(active_test=False).search(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)])
        result = super().unlink()
        documents.unlink()
        return result
