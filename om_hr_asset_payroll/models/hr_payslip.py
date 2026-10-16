from odoo import fields, models

ASSET_CODE = 'ASSET'


class HrAssetAssignment(models.Model):
    _inherit = 'hr.asset.assignment'

    payslip_id = fields.Many2one('hr.payslip', string='Deducted On', readonly=True, copy=False,
                                 index='btree_not_null', ondelete='set null',
                                 groups='om_hr_payroll.group_hr_payroll_user')


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        self._hr_asset_sync()
        return super().compute_sheet()

    def _hr_asset_sync(self):
        """ Give each payslip the asset charges of its employee up to the end of its period not deducted yet, as
            the input ASSET read by the asset rule. The final settlement of an exit takes them all. """
        Assignment = self.env['hr.asset.assignment'].sudo()
        for payslip in self.filtered(lambda p: not p.credit_note and p.state not in ('done', 'cancel')):
            Assignment.search([('payslip_id', '=', payslip.id)]).payslip_id = False
            domain = [
                ('employee_id', '=', payslip.employee_id.id),
                ('state', 'in', ('returned', 'lost')),
                ('charge_amount', '>', 0),
                '|', ('payslip_id', '=', False), ('payslip_id.state', '=', 'cancel'),
            ]
            if not ('exit_id' in payslip._fields and payslip.exit_id):
                domain.append(('date_to', '<=', payslip.date_to))
            charges = Assignment.search(domain)
            charges.payslip_id = payslip
            amount = sum(charges.mapped('charge_amount'))
            inputs = payslip.input_line_ids.filtered(lambda line: line.code == ASSET_CODE)
            if inputs:
                inputs[0].amount = amount
                inputs[1:].unlink()
            elif amount:
                version = payslip.version_id or self.env['hr.version'].browse(
                    self.get_versions(payslip.employee_id, payslip.date_from, payslip.date_to)[:1])
                if version:
                    payslip.input_line_ids = [(0, 0, {
                        'name': self.env._('Asset Charges'), 'code': ASSET_CODE, 'amount': amount,
                        'version_id': version.id, 'sequence': 91,
                    })]

    def _hr_asset_release(self):
        """ The charges of the payslips are to deduct again: the payslip is cancelled or refunded. """
        self.env['hr.asset.assignment'].sudo().search(
            [('payslip_id', 'in', self.filtered(lambda p: not p.credit_note).ids)]).payslip_id = False

    def action_payslip_cancel(self):
        self._hr_asset_release()
        return super().action_payslip_cancel()

    def refund_sheet(self):
        self._hr_asset_release()
        return super().refund_sheet()
