from odoo import fields, models


class HrPayrollExportWizard(models.TransientModel):
    """ The bank file of confirmed payslips: the export of File Layouts, for the payslips. """
    _name = 'hr.payroll.export.wizard'
    _inherit = 'file.export.wizard'
    _description = 'Export a Bank File'

    layout_id = fields.Many2one(domain="[('model', '=', 'hr.payslip')]")
