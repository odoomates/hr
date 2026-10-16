from odoo import _, fields, models
from odoo.exceptions import UserError

TODO = 'mail.mail_activity_data_todo'


class OmHrExit(models.Model):
    _inherit = 'om.hr.exit'

    def _create_clearance(self):
        super()._create_clearance()
        for exit_ in self:
            assignments = self.env['om.hr.asset.assignment'].sudo().search(
                [('employee_id', '=', exit_.employee_id.id), ('state', '=', 'assigned')])
            for assignment in assignments:
                equipment = assignment.equipment_id
                responsible = equipment.technician_user_id or equipment.category_id.technician_user_id
                line = self.env['om.hr.exit.clearance'].create({
                    'exit_id': exit_.id,
                    'sequence': 900,
                    'name': _('Return: %s', equipment.display_name),
                    'description': _('Return the asset, or report it lost, from the asset form.'),
                    'responsible_user_ids': responsible.ids,
                    'asset_assignment_id': assignment.id,
                })
                for user in line.responsible_user_ids:
                    exit_.activity_schedule(TODO, date_deadline=exit_.last_working_day, user_id=user.id,
                                            summary=line._activity_summary(), note=line.description)


class OmHrExitClearance(models.Model):
    _inherit = 'om.hr.exit.clearance'

    asset_assignment_id = fields.Many2one('om.hr.asset.assignment', string='Asset', readonly=True,
                                          ondelete='set null')

    def _close(self, state):
        held = self.filtered(lambda line: line.asset_assignment_id.state == 'assigned')
        if held:
            raise UserError(_('%s is still with the employee: return it, or report it lost, from the asset form.',
                              held[0].asset_assignment_id.equipment_id.display_name))
        return super()._close(state)

    def _close_returned(self):
        """ Cleared by the return of the asset, whoever takes it back. """
        for line in self:
            line.write({'state': 'done', 'user_id': self.env.user.id, 'date': fields.Date.context_today(self),
                        'note': _('Asset returned') if line.asset_assignment_id.state == 'returned'
                        else _('Asset reported lost')})
            summary = line._activity_summary()
            line.exit_id.sudo().activity_ids.filtered(lambda activity: activity.summary == summary).action_feedback(
                feedback=_('Cleared'))
