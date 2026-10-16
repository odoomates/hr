from dateutil.relativedelta import relativedelta

from odoo import _, fields, models


class HrAppraisalVersion(models.TransientModel):
    """ Record what an appraisal decided, e.g. a raise or a promotion, as a new version of the contract: the
    employee then opens on that version to change its wage, job or department, as for any other change. """
    _name = 'hr.appraisal.version'
    _description = 'New Contract Version from an Appraisal'

    appraisal_id = fields.Many2one('hr.appraisal', required=True, readonly=True)
    employee_id = fields.Many2one(related='appraisal_id.employee_id')
    date_version = fields.Date(
        string='Effective From', required=True,
        default=lambda self: fields.Date.context_today(self) + relativedelta(months=1, day=1),
        help='A date in the past is paid with the Retro Pay of the payroll.')

    def action_create(self):
        self.ensure_one()
        self.appraisal_id._check_roles('hr')
        version = self.employee_id.create_version({'date_version': self.date_version})
        self.appraisal_id.message_post(body=_('New contract version from %s.', fields.Date.to_string(
            self.date_version)))
        return version.action_open_version()
