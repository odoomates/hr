from odoo import models


class HrPolicyAssignment(models.Model):
    _inherit = 'hr.policy.assignment'

    def _get_my_url(self):
        """ The employees of the portal answer on the website. """
        url = super()._get_my_url()
        if url or not self.employee_id.user_id:
            return url
        return '%s/my/hr/policies/%s' % (self.get_base_url(), self.id)
