from odoo import models


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'om.document.mixin']

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
