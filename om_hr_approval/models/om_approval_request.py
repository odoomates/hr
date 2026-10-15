from odoo import models


class OmApprovalRequest(models.Model):
    _inherit = 'om.approval.request'

    def _excluded_approvers(self):
        """ The employee a request is for does not approve it either, e.g. when HR asks on his behalf. """
        users = super()._excluded_approvers()
        record = self._record()
        if record is not None:
            users |= self.env['om.approval.step']._employee_of(self, record).sudo().user_id
        return users
