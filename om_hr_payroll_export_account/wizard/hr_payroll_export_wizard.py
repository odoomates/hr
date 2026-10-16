from odoo import api, fields, models
from odoo.exceptions import UserError


class HrPayrollExportWizard(models.TransientModel):
    _inherit = 'hr.payroll.export.wizard'

    register_payment = fields.Boolean(
        string='Register the Payments',
        help='Also register the salary payments of the payslips in the file, as Pay Salaries does.')
    journal_id = fields.Many2one(
        'account.journal', string='Bank Journal', compute='_compute_journal_id', store=True, readonly=False,
        domain="[('type', '=', 'bank'), ('company_id', 'in', allowed_company_ids)]")
    payment_date = fields.Date(default=fields.Date.context_today)

    @api.depends('register_payment')
    def _compute_journal_id(self):
        for wizard in self:
            if wizard.register_payment and not wizard.journal_id:
                wizard.journal_id = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(self.env.company),
                    ('type', '=', 'bank')], limit=1)

    def action_download(self):
        action = super().action_download()
        if self.register_payment:
            self._register_payments()
        return action

    def _register_payments(self):
        """ The payments of the payslips of the file still to pay, through the payment register of the
            payroll accounting. """
        self.ensure_one()
        if not self.journal_id:
            raise UserError(self.env._('Choose the bank journal paying the salaries.'))
        payslips = self._get_records().filtered(lambda slip: slip._can_register_payment())
        if not payslips:
            return
        register = self.env['hr.payslip.payment.register'].with_context(
            default_payslip_ids=payslips.ids).create({
                'journal_id': self.journal_id.id,
                'payment_date': self.payment_date,
            })
        register.action_create_payments()
