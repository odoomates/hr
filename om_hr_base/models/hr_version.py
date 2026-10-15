from odoo import fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    type_id = fields.Many2one('hr.employee.type', string="Employee Category",
                              required=True, help="Employee category",
                              default=lambda self: self.env['hr.employee.type'].search([], limit=1))
