from odoo import _, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    om_appraisal_count = fields.Integer(compute='_compute_om_appraisal', groups='hr.group_hr_user')
    om_last_appraisal_date = fields.Date(string='Last Appraisal', compute='_compute_om_appraisal',
                                         groups='hr.group_hr_user')
    om_next_appraisal_date = fields.Date(string='Next Appraisal', compute='_compute_om_appraisal',
                                         groups='hr.group_hr_user')

    def _compute_om_appraisal(self):
        Appraisal = self.env['om.hr.appraisal']
        counts = dict(Appraisal._read_group([('employee_id', 'in', self.ids)], ['employee_id'], ['__count']))
        for employee in self:
            employee.om_appraisal_count = counts.get(employee, 0)
            last = Appraisal.search([('employee_id', '=', employee.id), ('state', '=', 'done')],
                                    order='date_done desc', limit=1)
            employee.om_last_appraisal_date = last.date_done
            employee.om_next_appraisal_date = employee._om_next_appraisal_date()

    def _om_next_appraisal_date(self):
        self.ensure_one()
        return self.env['om.hr.appraisal']._next_date(self)

    def action_open_om_appraisals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appraisals of %s', self.name),
            'res_model': 'om.hr.appraisal',
            'view_mode': 'list,kanban,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
