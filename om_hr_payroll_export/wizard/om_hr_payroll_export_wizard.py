from odoo import fields, models


class OmHrPayrollExportWizard(models.TransientModel):
    """ The bank file of confirmed payslips: the export of File Layouts, for the payslips. """
    _name = 'om.hr.payroll.export.wizard'
    _inherit = 'om.file.export.wizard'
    _description = 'Export a Bank File'

    layout_id = fields.Many2one(domain="[('model', '=', 'hr.payslip')]")
