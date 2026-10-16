from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    appraisal_probation = fields.Boolean(
        string='Probation Reviews', default=True,
        help='Create a review for the manager before the end of the trial period of a contract.')
    appraisal_probation_days = fields.Integer(string='Probation Review Lead', default=14)
    appraisal_auto = fields.Boolean(
        string='Plan the Appraisals', default=True,
        help='Create the appraisals of the employees on their own: the first one some months after they join, '
             'then at a regular interval.')
    appraisal_first_months = fields.Integer(string='First Appraisal After', default=6)
    appraisal_interval_months = fields.Integer(string='Then Every', default=12)
    appraisal_lead_days = fields.Integer(string='Created Ahead', default=30,
                                            help='How many days before it is due an appraisal is created.')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    appraisal_probation = fields.Boolean(related='company_id.appraisal_probation', readonly=False)
    appraisal_probation_days = fields.Integer(related='company_id.appraisal_probation_days', readonly=False)
    appraisal_auto = fields.Boolean(related='company_id.appraisal_auto', readonly=False)
    appraisal_first_months = fields.Integer(related='company_id.appraisal_first_months', readonly=False)
    appraisal_interval_months = fields.Integer(related='company_id.appraisal_interval_months', readonly=False)
    appraisal_lead_days = fields.Integer(related='company_id.appraisal_lead_days', readonly=False)
