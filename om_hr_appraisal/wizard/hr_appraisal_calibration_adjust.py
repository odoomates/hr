from odoo import api, fields, models
from odoo.exceptions import UserError

from ..models.hr_appraisal import LEVELS


class HrAppraisalCalibrationAdjust(models.TransientModel):
    """ Changes the rating or the potential of an appraisal in a calibration session, and logs why. """
    _name = 'hr.appraisal.calibration.adjust'
    _description = 'Adjust in Calibration'

    calibration_id = fields.Many2one('hr.appraisal.calibration', required=True, readonly=True)
    appraisal_id = fields.Many2one('hr.appraisal', required=True, readonly=True)
    rating_id = fields.Many2one('hr.appraisal.rating', required=True)
    potential = fields.Selection(LEVELS)
    reason = fields.Text(required=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        appraisal = self.env['hr.appraisal'].browse(values.get('appraisal_id') or self.env.context.get('appraisal_id'))
        if appraisal:
            values.update(appraisal_id=appraisal.id, rating_id=appraisal.rating_id.id,
                          potential=appraisal.sudo().potential_level)
        return values

    def action_apply(self):
        self.ensure_one()
        session, appraisal = self.calibration_id, self.appraisal_id
        if session.state != 'running':
            raise UserError(self.env._('Start %s to adjust its appraisals.', session.name))
        if appraisal not in session.appraisal_ids:
            raise UserError(self.env._('%s is not in this session.', appraisal.name))
        labels = dict(LEVELS)
        logs = []
        if self.rating_id != appraisal.rating_id:
            logs.append({'what': 'rating', 'old_value': appraisal.rating_id.name, 'new_value': self.rating_id.name})
        potential = appraisal.sudo().potential_level
        if self.potential != potential:
            logs.append({'what': 'potential', 'old_value': labels.get(potential),
                         'new_value': labels.get(self.potential)})
        if not logs:
            raise UserError(self.env._('Change the rating or the potential of %s first.', appraisal.employee_id.name))
        appraisal.write({'rating_id': self.rating_id.id})
        appraisal.sudo().potential_level = self.potential
        self.env['hr.appraisal.calibration.log'].create([
            dict(log, calibration_id=session.id, appraisal_id=appraisal.id, reason=self.reason) for log in logs])
        return {'type': 'ir.actions.act_window_close'}
