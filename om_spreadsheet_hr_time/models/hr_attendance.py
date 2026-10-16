from odoo import fields, models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # the department of core is not stored: the dashboard groups and filters the attendances by this one
    employee_department_id = fields.Many2one('hr.department', string='Department (Dashboard)',
                                       related='employee_id.department_id', store=True, index='btree_not_null')
