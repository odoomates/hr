from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class HrAppraisalCycle(models.Model):
    """ A review round, e.g. the annual review of 2026: one appraisal for each employee taking part. """
    _name = 'hr.appraisal.cycle'
    _inherit = ['mail.thread']
    _description = 'Appraisal Cycle'
    _check_company_auto = True
    _order = 'date_start desc, id desc'

    name = fields.Char(required=True, tracking=True)
    date_start = fields.Date(string='Period From', required=True)
    date_end = fields.Date(string='Period To', required=True)
    date_deadline = fields.Date(string='Deadline', required=True, tracking=True,
                                default=lambda self: fields.Date.context_today(self) + timedelta(days=30))
    template_id = fields.Many2one('hr.appraisal.template', string='Feedback Template', check_company=True,
                                  help='Leave empty to use the template of the department of each employee.')
    department_ids = fields.Many2many('hr.department', string='Departments')
    employee_ids = fields.Many2many('hr.employee', string='Employees',
                                    help='Taking part besides the employees of the departments.')
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'), ('running', 'Running'), ('done', 'Closed')],
                             required=True, default='draft', tracking=True)
    appraisal_ids = fields.One2many('hr.appraisal', 'cycle_id', string='Appraisals')
    appraisal_count = fields.Integer(compute='_compute_progress')
    done_count = fields.Integer(compute='_compute_progress')
    progress = fields.Float(compute='_compute_progress')

    @api.depends('appraisal_ids.state')
    def _compute_progress(self):
        for cycle in self:
            appraisals = cycle.appraisal_ids.filtered(lambda appraisal: appraisal.state != 'cancel')
            cycle.appraisal_count = len(appraisals)
            cycle.done_count = len(appraisals.filtered(lambda appraisal: appraisal.state == 'done'))
            cycle.progress = 100.0 * cycle.done_count / cycle.appraisal_count if cycle.appraisal_count else 0.0

    def _get_employees(self):
        self.ensure_one()
        employees = self.employee_ids
        if self.department_ids:
            employees |= self.env['hr.employee'].search([
                ('department_id', 'child_of', self.department_ids.ids), ('company_id', '=', self.company_id.id)])
        return employees

    def action_generate(self):
        """ One appraisal, started, for each employee taking part who has none in the cycle yet. """
        for cycle in self:
            if cycle.state == 'done':
                raise UserError(self.env._('%s is closed.', cycle.name))
            employees = cycle._get_employees() - cycle.appraisal_ids.employee_id
            if not employees and not cycle.appraisal_ids:
                raise UserError(self.env._('Choose the departments or the employees of %s first.', cycle.name))
            appraisals = self.env['hr.appraisal'].create([{
                'employee_id': employee.id,
                'cycle_id': cycle.id,
                'date_deadline': cycle.date_deadline,
                'template_id': cycle.template_id.id,
            } for employee in employees])
            appraisals.action_start()
            cycle.state = 'running'
        return self.action_open_appraisals() if len(self) == 1 else True

    def action_close(self):
        self.state = 'done'
        return True

    def action_open_appraisals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'hr.appraisal',
            'view_mode': 'kanban,list,form',
            'domain': [('cycle_id', '=', self.id)],
            'context': {'default_cycle_id': self.id, 'default_date_deadline': self.date_deadline},
        }
