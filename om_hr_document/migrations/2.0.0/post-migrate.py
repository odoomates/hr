""" The documents of the employees moved from Document Expiry go to the folders of their employees. """
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    root = env.ref('om_document.folder_expiry', raise_if_not_found=False)
    if not version or not root:
        return
    documents = env['om.documents.document'].with_context(active_test=False).search([
        ('res_model', '=', 'hr.employee'), ('type_id', '!=', False), ('folder_id', 'child_of', root.id)])
    employees = env['hr.employee'].with_context(active_test=False).browse(set(documents.mapped('res_id'))).exists()
    moved = 0
    for employee in employees:
        folder = employee._get_documents_folder()
        ids = documents.filtered(lambda document: document.res_id == employee.id).ids
        # the move keeps the dates and authors of the documents, and logs nothing in their chatter
        cr.execute("UPDATE om_documents_document SET folder_id = %s, company_id = %s WHERE id IN %s",
                   [folder.id, folder.company_id.id or None, tuple(ids)])
        moved += len(ids)
    env.invalidate_all()
    _logger.info('HR Documents upgrade: %s documents moved to the folders of %s employees', moved, len(employees))
