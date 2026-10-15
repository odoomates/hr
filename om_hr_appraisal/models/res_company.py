from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    om_appraisal_probation = fields.Boolean(
        string='Probation Reviews', default=True,
        help='Create a review for the manager before the end of the trial period of a contract.')
    om_appraisal_probation_days = fields.Integer(string='Probation Review Lead', default=14)
    om_appraisal_auto = fields.Boolean(
        string='Plan the Appraisals', default=True,
        help='Create the appraisals of the employees on their own: the first one some months after they join, '
             'then at a regular interval.')
    om_appraisal_first_months = fields.Integer(string='First Appraisal After', default=6)
    om_appraisal_interval_months = fields.Integer(string='Then Every', default=12)
    om_appraisal_lead_days = fields.Integer(string='Created Ahead', default=30,
                                            help='How many days before it is due an appraisal is created.')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    om_appraisal_probation = fields.Boolean(related='company_id.om_appraisal_probation', readonly=False)
    om_appraisal_probation_days = fields.Integer(related='company_id.om_appraisal_probation_days', readonly=False)
    om_appraisal_auto = fields.Boolean(related='company_id.om_appraisal_auto', readonly=False)
    om_appraisal_first_months = fields.Integer(related='company_id.om_appraisal_first_months', readonly=False)
    om_appraisal_interval_months = fields.Integer(related='company_id.om_appraisal_interval_months', readonly=False)
    om_appraisal_lead_days = fields.Integer(related='company_id.om_appraisal_lead_days', readonly=False)
