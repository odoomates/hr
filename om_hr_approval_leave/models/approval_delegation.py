from odoo import fields, models


class ApprovalDelegation(models.Model):
    _inherit = 'approval.delegation'

    leave_id = fields.Many2one('hr.leave', string='Time Off', ondelete='cascade', index='btree_not_null',
                               readonly=True, help='The time off the delegation follows: it changes with it.')
