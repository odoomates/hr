from odoo import models


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'om.print.mixin']
