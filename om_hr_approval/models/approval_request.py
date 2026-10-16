from odoo import models


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    def _excluded_approvers(self):
        """ The employee a request is for does not approve it either, e.g. when HR asks on his behalf. """
        users = super()._excluded_approvers()
        record = self._record()
        if record is not None:
            users |= self.env['approval.step']._employee_of(self, record).sudo().user_id
        return users
