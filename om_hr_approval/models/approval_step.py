from odoo import api, fields, models


class OmApprovalStep(models.Model):
    _inherit = 'om.approval.step'

    approver_type = fields.Selection(selection_add=[
        ('manager', 'Manager of the Employee'),
        ('department', 'Manager of the Department'),
        ('coach', 'Coach of the Employee'),
        ('hr_responsible', 'HR Responsible of the Contract'),
    ], ondelete={'manager': 'cascade', 'department': 'cascade', 'coach': 'cascade', 'hr_responsible': 'cascade'})

    @api.model
    def _employee_of(self, request, record):
        """ The employee a record is about: the one a document of HR names, the employee of the record, else the
            employee of the requester, e.g. the salesperson confirming a sale order. """
        if hasattr(record, '_approval_employee'):
            return record._approval_employee()
        field = record._fields.get('employee_id')
        if field is not None and field.type == 'many2one' and field.comodel_name == 'hr.employee':
            return record.employee_id
        employees = request.requester_id.sudo().employee_ids
        return employees.filtered(lambda e: e.company_id == request.company_id)[:1] or employees[:1]

    def _approvers_manager(self, request, record):
        return self._employee_of(request, record).sudo().parent_id.user_id

    def _approvers_department(self, request, record):
        return self._employee_of(request, record).sudo().department_id.manager_id.user_id

    def _approvers_coach(self, request, record):
        return self._employee_of(request, record).sudo().coach_id.user_id

    def _approvers_hr_responsible(self, request, record):
        return self._employee_of(request, record).sudo().version_id.hr_responsible_id

    @api.model
    def _users_models(self):
        return super()._users_models() + ('hr.employee',)

    @api.model
    def _as_users(self, records):
        if records._name == 'hr.employee':
            return records.user_id
        return super()._as_users(records)
