from odoo import _, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    appraisal_count = fields.Integer(compute='_compute_appraisal', groups='hr.group_hr_user')
    last_appraisal_date = fields.Date(string='Last Appraisal', compute='_compute_appraisal',
                                         groups='hr.group_hr_user')
    next_appraisal_date = fields.Date(string='Next Appraisal', compute='_compute_appraisal',
                                         groups='hr.group_hr_user')

    def _compute_appraisal(self):
        Appraisal = self.env['hr.appraisal']
        counts = dict(Appraisal._read_group([('employee_id', 'in', self.ids)], ['employee_id'], ['__count']))
        for employee in self:
            employee.appraisal_count = counts.get(employee, 0)
            last = Appraisal.search([('employee_id', '=', employee.id), ('state', '=', 'done')],
                                    order='date_done desc', limit=1)
            employee.last_appraisal_date = last.date_done
            employee.next_appraisal_date = employee._next_appraisal_date()

    def _next_appraisal_date(self):
        self.ensure_one()
        return self.env['hr.appraisal']._next_date(self)

    def action_open_appraisals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appraisals of %s', self.name),
            'res_model': 'hr.appraisal',
            'view_mode': 'list,kanban,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
