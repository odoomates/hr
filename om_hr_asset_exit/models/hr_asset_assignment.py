from odoo import models


class HrAssetAssignment(models.Model):
    _inherit = 'hr.asset.assignment'

    def _on_closed(self):
        """ The asset is back, or lost: its line of the exit clearance is cleared. """
        result = super()._on_closed()
        lines = self.env['hr.exit.clearance'].sudo().search([
            ('asset_assignment_id', 'in', self.ids), ('state', '=', 'pending'),
            ('exit_id.state', '=', 'approved')])
        lines._close_returned()
        return result
