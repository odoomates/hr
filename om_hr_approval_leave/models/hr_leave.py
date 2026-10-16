from odoo import api, models


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.model_create_multi
    def create(self, vals_list):
        leaves = super().create(vals_list)
        leaves.filtered(lambda leave: leave.state == 'validate')._sync_approval_delegation()
        return leaves

    def write(self, vals):
        result = super().write(vals)
        if {'state', 'request_date_from', 'request_date_to', 'employee_id'} & set(vals):
            self._sync_approval_delegation()
        return result

    def _approval_substitute(self):
        """ :return: who approves for the employee during the time off: their substitute, else their manager """
        self.ensure_one()
        user = self.employee_id.user_id
        return user.approval_substitute_id or self.employee_id.parent_id.user_id

    def _sync_approval_delegation(self):
        """ The delegation of the approvals of the employee follows their validated time off. """
        # made by the time off, as the super user: the rights of a user delegating do not apply
        Delegation = self.env['approval.delegation'].sudo().with_context(active_test=False)
        for leave in self:
            delegation = Delegation.search([('leave_id', '=', leave.id)])
            user = leave.employee_id.user_id
            substitute = leave._approval_substitute() if user and not user.share else None
            if leave.state != 'validate' or not substitute or substitute == user:
                delegation.unlink()
                continue
            values = {
                'user_id': user.id,
                'delegate_id': substitute.id,
                'date_from': leave.request_date_from or leave.date_from.date(),
                'date_to': leave.request_date_to or leave.date_to.date(),
                'note': self.env._('Time off: %s', leave.display_name),
                'active': True,
            }
            if delegation:
                delegation.write(values)
            else:
                Delegation.create(dict(values, leave_id=leave.id))
