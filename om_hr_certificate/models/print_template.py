from odoo import fields, models


class PrintTemplate(models.Model):
    _inherit = 'print.template'

    employee_request = fields.Boolean(
        string='Employees Can Request',
        help='Employees ask for this certificate themselves; it is printed once approved.')
