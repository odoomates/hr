from odoo import fields, models


class HrLoanType(models.Model):
    """ A kind of loan and its limits, e.g. a salary advance repaid at once, or a personal loan over a year. """
    _name = 'hr.loan.type'
    _description = 'Loan Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company')
    is_advance = fields.Boolean(
        string='Salary Advance', help='Repaid at once, from the next salary: a single installment.')
    max_amount = fields.Float(string='Maximum Amount', help='0: no maximum.')
    max_installments = fields.Integer(string='Maximum Installments', help='0: no maximum.')
    max_wage_percent = fields.Float(
        string='Maximum Installment (% of Wage)',
        help='An installment cannot take more than this part of the wage, e.g. 50. 0: no maximum.')
    min_service_months = fields.Integer(
        string='Minimum Service (Months)', help='How long the employee must have worked for the company. 0: no minimum.')
    single_running = fields.Boolean(
        string='One at a Time', default=True,
        help='An employee asks for a new loan of this type once the previous one is repaid.')
    description = fields.Text(translate=True, help='Shown to the employee asking for a loan of this type.')
