from odoo import fields, models

from odoo.addons.om_hr_compensation.models.hr_version import band_position


class HrMeritCycle(models.Model):
    _inherit = 'hr.merit.cycle'

    def _line_values(self, employee):
        """ The last rating of the employee, and the raise the merit matrix suggests for it. """
        values = super()._line_values(employee)
        appraisal = self.env['hr.appraisal'].search(
            [('employee_id', '=', employee.id), ('state', '=', 'done'), ('rating_id', '!=', False)],
            order='date_done desc, id desc', limit=1)
        if appraisal:
            values['rating_id'] = appraisal.rating_id.id
            grade = self.env['hr.salary.grade'].browse(values.get('salary_grade_id'))
            position = band_position(values['current_wage'], grade)
            percent = self.env['hr.merit.matrix']._get_percent(appraisal.rating_id, position, self.company_id) \
                if position else None
            if percent is not None:
                values['proposed_percent'] = percent
        return values


class HrMeritCycleLine(models.Model):
    _inherit = 'hr.merit.cycle.line'

    rating_id = fields.Many2one('hr.appraisal.rating', string='Last Rating', readonly=True)
