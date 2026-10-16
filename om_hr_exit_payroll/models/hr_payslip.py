from odoo import fields, models

ENCASHMENT = 'LEAVE_ENCASH'
GRATUITY = 'GRATUITY'


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    exit_id = fields.Many2one('hr.exit', string='Final Settlement Of', index=True, copy=False, readonly=True,
                              help='The exit the payslip settles.', check_company=True)

    def compute_sheet(self):
        for payslip in self.filtered(lambda p: p.exit_id and p.state not in ('done', 'cancel')):
            payslip._hr_exit_set_inputs()
        return super().compute_sheet()

    def _get_contract_end(self, version):
        """ The final settlement pays up to the last working day, even before the departure ends the contract. """
        contract_end = super()._get_contract_end(version)
        last_day = self.exit_id.sudo().last_working_day
        if last_day and (not contract_end or last_day < contract_end):
            return last_day
        return contract_end

    def _hr_exit_set_inputs(self):
        """ The amounts of the final settlement, read again at each computation. """
        self.ensure_one()
        exit_ = self.exit_id.sudo()
        self._hr_exit_set_input(ENCASHMENT, self.env._('Unused Time Off'), exit_._hr_encashment_amount())
        gratuity = exit_.gratuity_amount if 'gratuity_amount' in exit_._fields else 0.0
        self._hr_exit_set_input(GRATUITY, self.env._('End of Service Gratuity'), gratuity)

    def _hr_exit_set_input(self, code, name, amount):
        inputs = self.input_line_ids.filtered(lambda line: line.code == code)
        if inputs:
            inputs[0].amount = amount
            inputs[1:].unlink()
        elif amount and self.version_id:
            self.input_line_ids = [(0, 0, {'name': name, 'code': code, 'amount': amount,
                                           'version_id': self.version_id.id, 'sequence': 95})]
