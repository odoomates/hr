from odoo import api, fields, models
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    file_export_ids = fields.Many2many('file.export', 'hr_payslip_om_file_export_rel', 'payslip_id',
                                          'export_id', string='Bank Files', readonly=True, copy=False)
    exported = fields.Boolean(string='In a Bank File', compute='_compute_exported', store=True)

    @api.depends('file_export_ids')
    def _compute_exported(self):
        for payslip in self:
            payslip.exported = bool(payslip.file_export_ids)

    def _net(self):
        self.ensure_one()
        return sum(self.line_ids.filtered(lambda line: line.code == 'NET').mapped('total'))

    def _bank_split(self, net):
        """ :return: the transfers of the net salary, as (bank account, amount), following the Salary
            Distribution of the employee: fixed amounts and percentages in order, the last account taking what
            the rounding leaves. """
        self.ensure_one()
        employee = self.employee_id.sudo()
        currency = self.company_id.currency_id
        distribution = employee.salary_distribution or {}
        banks = self.env['res.partner.bank'].sudo().browse([int(key) for key in distribution]).exists()
        banks = banks.sorted(lambda bank: distribution[str(bank.id)].get('sequence', 0))
        if not banks:
            return [(employee.primary_bank_account_id, net)]
        transfers, left = [], net
        for bank in banks[:-1]:
            share = distribution[str(bank.id)]
            amount = currency.round(net * share.get('amount', 0.0) / 100.0) if share.get('amount_is_percentage') \
                else min(currency.round(share.get('amount', 0.0)), left)
            transfers.append((bank, amount))
            left -= amount
        transfers.append((banks[-1], currency.round(left)))
        return [(bank, amount) for bank, amount in transfers if currency.compare_amounts(amount, 0) > 0]

    def _file_lines(self, layout):
        """ The lines of a bank file: one per salary transfer of the confirmed payslips, the net salary split
            over the bank accounts of the employee. """
        lines = []
        for payslip in self.sorted(lambda slip: (slip.employee_id.name or '', slip.id)):
            problems = []
            name = payslip.employee_id.name
            if payslip.state != 'done' or payslip.credit_note:
                continue
            if payslip.file_export_ids:
                problems.append(self.env._('%(employee)s: the payslip %(payslip)s is already in %(file)s.',
                                           employee=name, payslip=payslip.number,
                                           file=', '.join(payslip.file_export_ids.mapped('name'))))
            net = payslip._net()
            for bank, amount in payslip._bank_split(net):
                if not bank:
                    problems.append(self.env._('%s has no bank account.', name))
                elif not bank.allow_out_payment:
                    problems.append(self.env._('%(employee)s: the account %(account)s is not trusted for payments.',
                                               employee=name, account=bank.account_number))
                lines.append({
                    'record': payslip,
                    'object': payslip,
                    'payslip': payslip,
                    'employee': payslip.employee_id.sudo(),
                    'partner': payslip.employee_id.sudo().work_contact_id,
                    'bank': bank,
                    'amount': amount,
                    'net': net,
                    'batch': payslip.payslip_run_id,
                    'company': payslip.company_id,
                    'currency': payslip.company_id.currency_id,
                    'period_from': payslip.date_from,
                    'period_to': payslip.date_to,
                    'line': payslip._line_total,
                    'problems': problems,
                })
                problems = []
        return lines

    def _line_total(self, code):
        """ The total of the lines of a salary rule, e.g. line('BASIC') in a column. """
        return sum(self.line_ids.filtered(lambda line: line.code == code).mapped('total'))

    def _file_exported(self, export):
        self.filtered(lambda slip: slip.state == 'done' and not slip.credit_note).write(
            {'file_export_ids': [(4, export.id)]})

    def action_export_bank_file(self):
        payslips = self.filtered(lambda slip: slip.state == 'done' and not slip.credit_note)
        if not payslips:
            raise UserError(self.env._('Only the confirmed payslips are paid by bank: confirm them first.'))
        layout = self.env['file.layout'].search([('model', '=', 'hr.payslip')], limit=1)
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Export Bank File'),
            'res_model': 'hr.payroll.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_model': 'hr.payslip', 'active_ids': payslips.ids,
                        'default_layout_id': layout.id},
        }


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def action_export_bank_file(self):
        self.ensure_one()
        return self.slip_ids.action_export_bank_file()


