from odoo import Command, api, models


class ApprovalRule(models.Model):
    _inherit = 'approval.rule'

    @api.model
    def _gallery_templates(self):
        return super()._gallery_templates() + [{
            'key': 'hr_manager_hr', 'icon': 'account_tree', 'needs': ('document',),
            'name': self.env._('Manager, then HR'),
            'description': self.env._('An HR document, such as a loan or a request: the manager of the employee '
                                      'approves, then HR.'),
        }]

    @api.model
    def _gallery_flow_values(self, key, model, preset):
        if key != 'hr_manager_hr':
            return super()._gallery_flow_values(key, model, preset)
        hr_group = self.env.ref('hr.group_hr_manager')
        return {
            'name': self.env._('%s: manager, then HR', preset['label']),
            'self_approve': False,
            'fallback_group_id': hr_group.id,
            'step_ids': [
                Command.create({'name': self.env._('Manager'), 'approver_type': 'manager', 'remind_days': 2,
                                'escalate_days': 5, 'escalate_type': 'manager'}),
                Command.create({'name': self.env._('HR'), 'approver_type': 'group', 'group_id': hr_group.id,
                                'remind_days': 2}),
            ],
        }
