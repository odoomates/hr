from odoo import fields, models


class OmPrintTemplate(models.Model):
    _inherit = 'om.print.template'

    employee_request = fields.Boolean(
        string='Employees Can Request',
        help='Employees ask for this certificate themselves; it is printed once approved.')
