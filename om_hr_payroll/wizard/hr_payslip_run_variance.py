from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.tools.misc import format_amount


class HrPayslipRunVariance(models.TransientModel):
    """ Lists, before a batch is confirmed, the payslips whose gross or net pay changes by more than the threshold
    of the company from the last confirmed payslip of the employee, and the employees without one. """
    _name = 'hr.payslip.run.variance'
    _description = 'Payslip Batch Variance Check'

    payslip_run_id = fields.Many2one('hr.payslip.run', string='Batch', required=True, readonly=True)
    threshold = fields.Float(string='Threshold (%)', readonly=True)
    line_ids = fields.One2many('hr.payslip.run.variance.line', 'wizard_id', string='Payslips', readonly=True)

    @staticmethod
    def _totals(payslip):
        """ :return: the gross and net pay of the payslip, and the total and name of each of its rules """
        gross = net = 0.0
        rules = {}
        for line in payslip.line_ids:
            if line.category_id.code == 'GROSS':
                gross += line.total
            elif line.category_id.code == 'NET':
                net += line.total
            total, _name = rules.get(line.code, (0.0, line.name))
            rules[line.code] = (total + line.total, line.name)
        return gross, net, rules

    @staticmethod
    def _change(previous, current):
        """ :return: the change from `previous` to `current`, as a ratio of `previous` """
        if not previous:
            return 0.0 if not current else (1.0 if current > 0 else -1.0)
        return (current - previous) / abs(previous)

    def _get_previous(self, payslip):
        """ :return: the last payslip of the employee confirmed before the period of `payslip` """
        return self.env['hr.payslip'].search([
            ('employee_id', '=', payslip.employee_id.id),
            ('company_id', '=', payslip.company_id.id),
            ('state', '=', 'done'),
            ('credit_note', '=', False),
            ('date_to', '<', payslip.date_from),
        ], order='date_to desc, id desc', limit=1)

    @api.model
    def _create_for(self, payslip_run):
        """ :return: the check of the batch, or nothing when the check is off or no payslip needs one """
        threshold = payslip_run.company_id.om_payroll_variance_threshold
        payslips = payslip_run.slip_ids.filtered(lambda payslip: payslip.state in ('draft', 'verify'))
        if threshold <= 0 or not payslips:
            return self.browse()
        # computed as Mark as Done does: the check reads the amounts about to be confirmed
        payslips.compute_sheet()
        lines = []
        for payslip in payslips:
            gross, net, rules = self._totals(payslip)
            values = {'payslip_id': payslip.id, 'gross': gross, 'net': net}
            previous = self._get_previous(payslip)
            if not previous:
                lines.append(dict(values, reason='first'))
                continue
            previous_gross, previous_net, previous_rules = self._totals(previous)
            gross_change = self._change(previous_gross, gross)
            net_change = self._change(previous_net, net)
            if max(abs(gross_change), abs(net_change)) * 100 <= threshold:
                continue
            # the rule which moved most, as a first hint of the reason
            differences = {
                code: rules.get(code, (0.0, ''))[0] - previous_rules.get(code, (0.0, ''))[0]
                for code in rules.keys() | previous_rules.keys()
            }
            top_code = max(sorted(differences), key=lambda code: abs(differences[code]))
            lines.append(dict(
                values, reason='variance', previous_payslip_id=previous.id,
                previous_gross=previous_gross, gross_change=gross_change,
                previous_net=previous_net, net_change=net_change,
                top_rule=(rules.get(top_code) or previous_rules[top_code])[1],
                top_difference=differences[top_code],
            ))
        if not lines:
            return self.browse()
        return self.create({
            'payslip_run_id': payslip_run.id,
            'threshold': threshold,
            'line_ids': [fields.Command.create(line) for line in lines],
        })

    def _get_action(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Check the Payslips'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_confirm(self):
        """ Confirms the batch as listed, and keeps the list in its chatter. """
        self.ensure_one()
        items = Markup().join(Markup('<li>%s: %s</li>') % (line.employee_id.name, line._get_summary())
                              for line in self.line_ids)
        self.payslip_run_id.message_post(body=Markup('%s<ul>%s</ul>') % (
            _('Confirmed after the variance check (threshold %g%%):', self.threshold), items))
        self.payslip_run_id.done_payslip_run()
        return {'type': 'ir.actions.act_window_close'}


class HrPayslipRunVarianceLine(models.TransientModel):
    _name = 'hr.payslip.run.variance.line'
    _description = 'Payslip Batch Variance Check Line'

    wizard_id = fields.Many2one('hr.payslip.run.variance', required=True, ondelete='cascade')
    payslip_id = fields.Many2one('hr.payslip', string='Payslip', required=True)
    employee_id = fields.Many2one(related='payslip_id.employee_id')
    currency_id = fields.Many2one(related='payslip_id.company_id.currency_id')
    reason = fields.Selection([
        ('variance', 'Above the threshold'),
        ('first', 'No previous payslip'),
    ], required=True)
    previous_payslip_id = fields.Many2one('hr.payslip', string='Previous Payslip')
    previous_gross = fields.Monetary(string='Previous Gross')
    gross = fields.Monetary(string='Gross')
    gross_change = fields.Float(string='Gross Change')
    previous_net = fields.Monetary(string='Previous Net')
    net = fields.Monetary(string='Net')
    net_change = fields.Float(string='Net Change')
    top_rule = fields.Char(string='Biggest Change', help='The salary rule whose amount changed most.')
    top_difference = fields.Monetary(string='Difference')

    def _get_summary(self):
        self.ensure_one()
        if self.reason == 'first':
            return _('no previous payslip, net %s', format_amount(self.env, self.net, self.currency_id))
        return _('net %(previous)s to %(net)s (%(change)+.1f%%), mostly %(rule)s',
                 previous=format_amount(self.env, self.previous_net, self.currency_id),
                 net=format_amount(self.env, self.net, self.currency_id),
                 change=self.net_change * 100, rule=self.top_rule)

    def action_open_payslip(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'res_id': self.payslip_id.id,
            'view_mode': 'form',
        }
