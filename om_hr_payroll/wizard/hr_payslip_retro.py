from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date

# the categories the pay is compared on: what the employee earns, before the deductions
RETRO_CATEGORIES = ('BASIC', 'ALW')


class HrPayslipRetro(models.TransientModel):
    """ Pays on a draft payslip what the payslips already confirmed would have paid with the versions as they
    stand now, e.g. after a raise dated back to a past month. """
    _name = 'hr.payslip.retro'
    _description = 'Retro Pay'

    payslip_id = fields.Many2one('hr.payslip', string='Payslip', required=True, readonly=True)
    date_from = fields.Date(string='From', required=True,
        help="The confirmed payslips of the employee from this date up to this payslip are computed again.")

    @staticmethod
    def _earned(payslip):
        """ :return: the total of the lines of the payslip in the Basic and Allowance categories """
        total = 0.0
        for line in payslip.line_ids:
            category = line.category_id
            while category and category.code not in RETRO_CATEGORIES:
                category = category.parent_id
            if category:
                total += line.total
        return total

    def action_apply(self):
        self.ensure_one()
        payslip = self.payslip_id
        if payslip.state != 'draft':
            raise UserError(_('Retro pay is added to a draft payslip.'))
        Payslip = self.env['hr.payslip']
        originals = Payslip.search([
            ('employee_id', '=', payslip.employee_id.id),
            ('state', '=', 'done'),
            ('credit_note', '=', False),
            ('date_from', '>=', self.date_from),
            ('date_to', '<', payslip.date_from),
        ], order='date_from')
        if not originals:
            raise UserError(_('%s has no confirmed payslip from %s to this payslip.',
                              payslip.employee_id.name, format_date(self.env, self.date_from)))

        difference = 0.0
        for original in originals:
            versions = Payslip.get_versions(original.employee_id, original.date_from, original.date_to)
            if not versions:
                continue
            earned = self._earned(original)
            # computed on a copy that is rolled back: nothing of it stays, and no payslip number is used up
            with self.env.cr.savepoint() as savepoint:
                copy = original.copy({'number': 'RETRO', 'version_id': versions[0], 'name': original.name})
                copy.compute_sheet()
                difference += self._earned(copy) - earned
                savepoint.close(rollback=True)
            self.env.invalidate_all()

        months = ', '.join(dict.fromkeys(
            format_date(self.env, original.date_from, date_format='MMMM y') for original in originals))
        values = {'name': _('Retro Pay: %s', months), 'amount': payslip.company_id.currency_id.round(difference)}
        line = payslip.input_line_ids.filtered(lambda line: line.code == 'RETRO')[:1]
        if line:
            line.write(values)
        else:
            version = payslip.version_id or self.env['hr.version'].browse(Payslip.get_versions(
                payslip.employee_id, payslip.date_from, payslip.date_to)[:1])
            if not version:
                raise UserError(_('%s has no contract in the period of the payslip.', payslip.employee_id.name))
            payslip.input_line_ids = [(0, 0, dict(values, code='RETRO', version_id=version.id))]
        payslip.compute_sheet()
        return True
