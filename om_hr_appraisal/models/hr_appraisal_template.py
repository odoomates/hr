from odoo import api, fields, models


class HrAppraisalTemplate(models.Model):
    """ The questions an appraisal starts from, for the employee and for the manager. """
    _name = 'hr.appraisal.template'
    _description = 'Appraisal Feedback Template'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    employee_feedback = fields.Html(string="Employee's Feedback", translate=True)
    manager_feedback = fields.Html(string="Manager's Feedback", translate=True)
    department_ids = fields.Many2many(
        'hr.department', string='Departments',
        help='Used for the employees of these departments. Leave empty to use it for everyone else.')
    company_id = fields.Many2one('res.company', string='Company',
                                 help='Leave empty to share the template with all the companies.')

    @api.model
    def _get_for_employee(self, employee):
        """ :return: the template of the department of the employee, else the first one for everyone """
        templates = self.search(['|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id)])
        return templates.filtered(lambda t: employee.department_id in t.department_ids)[:1] \
            or templates.filtered(lambda t: not t.department_ids)[:1]


class HrAppraisalRating(models.Model):
    """ The overall rating a manager gives at the end of an appraisal. """
    _name = 'hr.appraisal.rating'
    _description = 'Appraisal Rating'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Char(translate=True)
