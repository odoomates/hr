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
    group_goal_alignment = fields.Boolean(
        string='Goal Alignment', implied_group='om_hr_appraisal.group_goal_alignment',
        help='Goals of the company and of the departments, served by the goals of the employees.')
    group_one_on_one = fields.Boolean(
        string='One-on-Ones', implied_group='om_hr_appraisal.group_one_on_one',
        help='Regular meetings of the managers with each employee, with their notes and actions.')
    group_calibration = fields.Boolean(
        string='9-Box and Calibration', implied_group='om_hr_appraisal.group_calibration',
        help='The potential of the employees next to their rating, the 9-box grid and the calibration sessions.')
    module_om_hr_appraisal_survey = fields.Boolean(string='360 Feedback')
