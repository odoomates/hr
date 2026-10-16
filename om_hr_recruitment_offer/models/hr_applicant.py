from odoo import _, fields, models


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    offer_ids = fields.One2many('hr.applicant.offer', 'applicant_id', string='Offers')
    offer_count = fields.Integer(compute='_compute_offer_count', string='Number of Offers')

    def _compute_offer_count(self):
        counts = dict(self.env['hr.applicant.offer']._read_group(
            [('applicant_id', 'in', self.ids)], ['applicant_id'], ['__count']))
        for applicant in self:
            applicant.offer_count = counts.get(applicant, 0)

    def _get_hired_stage(self):
        """ :return: the first hired stage of the job of the applicant, else of every job """
        self.ensure_one()
        Stage = self.env['hr.recruitment.stage']
        stages = Stage.search([('hired_stage', '=', True)], order='sequence, id')
        return stages.filtered(lambda stage: self.job_id in stage.job_ids)[:1] or \
            stages.filtered(lambda stage: not stage.job_ids)[:1]

    def _accepted_offer(self):
        self.ensure_one()
        return self.offer_ids.filtered(lambda offer: offer.state == 'accepted').sorted('date_accepted')[-1:]

    def _get_employee_create_vals(self):
        values = super()._get_employee_create_vals()
        offer = self._accepted_offer()
        if offer:
            values.update(offer._employee_values())
        return values

    def create_employee_from_applicant(self):
        """ The department and the job of the accepted offer win over those of the applicant, which core writes
            again on the employee. """
        action = super().create_employee_from_applicant()
        offer = self._accepted_offer()
        if offer and self.employee_id:
            values = offer._employee_values()
            self.employee_id.write({key: values[key] for key in ('job_id', 'job_title', 'department_id')
                                    if key in values})
        return action

    def action_new_offer(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Offer'),
            'res_model': 'hr.applicant.offer',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'context': {
                'default_applicant_id': self.id,
                'default_job_id': self.job_id.id,
                'default_department_id': self.department_id.id,
                'default_wage': self.salary_proposed or self.salary_expected,
                'default_date_start': self.availability,
            },
        }

    def action_open_offers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Offers'),
            'res_model': 'hr.applicant.offer',
            'view_mode': 'list,form',
            'domain': [('applicant_id', '=', self.id)],
            'context': {'default_applicant_id': self.id},
        }
