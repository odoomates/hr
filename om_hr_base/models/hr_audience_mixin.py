from odoo import api, fields, models

AUDIENCES = [
    ('company', 'The Whole Company'),
    ('department', 'Departments'),
    ('job', 'Job Positions'),
    ('tag', 'Employee Tags'),
    ('employee', 'Employees'),
]


class HrAudienceMixin(models.AbstractModel):
    """ Whom a record is for: the employees of a company, of departments, of job positions, of tags, or some
    employees, e.g. the readers of an announcement or the employees agreeing to a policy. """
    _name = 'hr.audience.mixin'
    _description = 'Employees Reached'

    company_id = fields.Many2one('res.company', required=True, index=True,
                                 default=lambda self: self.env.company)
    audience = fields.Selection(AUDIENCES, required=True, default='company')
    department_ids = fields.Many2many('hr.department', string='Departments',
                                      help='Their sub-departments included.')
    job_ids = fields.Many2many('hr.job', string='Job Positions')
    category_ids = fields.Many2many('hr.employee.category', string='Employee Tags')
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    audience_count = fields.Integer(compute='_compute_audience_count', string='Employees Reached')

    @api.depends('audience', 'department_ids', 'job_ids', 'category_ids', 'employee_ids', 'company_id')
    def _compute_audience_count(self):
        for record in self:
            record.audience_count = len(record._audience())

    def _audience_domain(self):
        """ :return: the domain of the employees reached, or None when nobody is """
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id)]
        if self.audience == 'department':
            if not self.department_ids:
                return None
            domain.append(('department_id', 'child_of', self.department_ids.ids))
        elif self.audience == 'job':
            domain.append(('job_id', 'in', self.job_ids.ids))
        elif self.audience == 'tag':
            domain.append(('category_ids', 'in', self.category_ids.ids))
        elif self.audience == 'employee':
            domain.append(('id', 'in', self.employee_ids.ids))
        return domain

    def _audience(self):
        """ :return: the employees reached """
        self.ensure_one()
        Employee = self.env['hr.employee'].sudo()
        domain = self._audience_domain()
        return Employee.search(domain) if domain is not None else Employee

    def _in_audience(self, employees):
        """ :return: the employees of `employees` the record reaches """
        self.ensure_one()
        domain = self._audience_domain()
        if domain is None or not employees:
            return self.env['hr.employee']
        return self.env['hr.employee'].sudo().search(domain + [('id', 'in', employees.ids)])
