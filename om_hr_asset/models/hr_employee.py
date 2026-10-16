from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    asset_assignment_ids = fields.One2many('hr.asset.assignment', 'employee_id', string='Assets',
                                              groups='hr.group_hr_user')
