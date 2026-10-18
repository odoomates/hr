from odoo import api, fields, models
from odoo.tools.misc import format_date


class AnnualStatementReport(models.AbstractModel):
    """ What the employee was paid over a payroll year: the total of each salary rule shown on the payslips,
    month by month, from the confirmed payslips; a refund is taken back in the month of the payslip it refunds. """
    _name = 'report.om_hr_payroll.report_annual_statement'
    _description = 'Payroll Annual Statement'

    @api.model
    def _get_statement(self, employee, year=None):
        """ :return: the statement of the payroll year starting in `year`, by default the current one """
        Payslip = self.env['hr.payslip']
        if not year:
            year = Payslip._get_year_start(fields.Date.context_today(self), employee.company_id).year
        date_from, date_to = Payslip._get_tax_year(year, employee.company_id)
        payslips = Payslip.search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'done'),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
        ], order='date_to, id')
        months = []
        rows = {}
        for payslip in payslips:
            month = payslip.date_to.replace(day=1)
            if month not in months:
                months.append(month)
            sign = -1.0 if payslip.credit_note else 1.0
            for line in payslip.line_ids.filtered('appears_on_payslip'):
                row = rows.setdefault(line.code, {
                    'code': line.code, 'name': line.name, 'sequence': line.sequence,
                    'net': line.category_id.code == 'NET', 'amounts': {}, 'total': 0.0,
                })
                row['amounts'][month] = row['amounts'].get(month, 0.0) + sign * line.total
                row['total'] += sign * line.total
        return {
            'employee': employee,
            'currency': employee.company_id.currency_id,
            'date_from': date_from,
            'date_to': date_to,
            'months': [(month, format_date(self.env, month, date_format='MMM yy')) for month in sorted(months)],
            'rows': sorted(rows.values(), key=lambda row: (row['sequence'], row['code'])),
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        employees = self.env['hr.employee'].browse(docids)
        year = (data or {}).get('year')
        return {
            'doc_ids': docids,
            'doc_model': 'hr.employee',
            'docs': employees,
            'statements': [self._get_statement(employee, year and int(year)) for employee in employees],
        }
