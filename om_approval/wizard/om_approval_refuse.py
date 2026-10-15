from odoo import fields, models


class OmApprovalRefuse(models.TransientModel):
    _name = 'om.approval.refuse'
    _description = 'Refuse an Approval'

    request_id = fields.Many2one('om.approval.request', required=True, ondelete='cascade')
    reason = fields.Text(required=True)

    def action_refuse(self):
        self.ensure_one()
        self.request_id.action_refuse(self.reason)
        return {'type': 'ir.actions.act_window_close'}
