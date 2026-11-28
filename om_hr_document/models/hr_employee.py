from odoo import fields, models


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'om.documents.expiry.mixin']

    documents_folder_id = fields.Many2one('om.documents.folder', string='Documents Folder', copy=False,
                                          groups='hr.group_hr_user', ondelete='set null')

    def _get_documents_folder(self):
        """ The folder of the employee in the Employees folder of Documents, created the first time: the HR
        officers reach it, the other users do not. """
        self.ensure_one()
        root = self.env.ref('om_hr_document.folder_employees', raise_if_not_found=False)
        if not root:
            return super()._get_documents_folder()
        return self.sudo()._om_documents_record_folder(root.sudo(), 'documents_folder_id').with_env(self.env)

    def _get_documents_values(self):
        return dict(super()._get_documents_values(), partner_id=self.work_contact_id.id)

    def _document_responsible_users(self):
        """ The HR responsible of the contract, else the HR managers of the company. """
        self.ensure_one()
        responsible = self.sudo().version_id.hr_responsible_id
        if responsible:
            return responsible
        return self.env.ref('hr.group_hr_manager').sudo().all_user_ids.filtered(
            lambda user: self.company_id in user.company_ids and not user.share)

    def _document_holder_partner(self):
        self.ensure_one()
        return self.sudo().work_contact_id
