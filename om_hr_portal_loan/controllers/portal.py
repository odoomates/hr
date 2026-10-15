from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from odoo.addons.om_hr_portal.controllers.portal import OmHrPortal


class OmHrPortalLoan(OmHrPortal):

    def _om_loan_page(self, error=None, form=None):
        employee = self._om_employee()
        loans = request.env['om.hr.loan'].sudo().search([('employee_id', '=', employee.id)])
        types = request.env['om.hr.loan.type'].sudo().search(
            ['|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id)])
        return request.render('om_hr_portal_loan.portal_my_loans', self._om_values(
            'om_hr_loans', loans=loans, loan_types=types, error=error, form=form or {}, om_section='Loans'))

    @http.route('/my/hr/loans', type='http', auth='user', website=True)
    def om_hr_loans(self, **kwargs):
        return self._om_loan_page()

    @http.route('/my/hr/loans/<int:loan_id>', type='http', auth='user', website=True)
    def om_hr_loan(self, loan_id, **kwargs):
        loan = self._om_own('om.hr.loan', loan_id)
        return request.render('om_hr_portal_loan.portal_my_loan', self._om_values(
            'om_hr_loan', loan=loan, om_section='Loans', om_section_url='/my/hr/loans', om_record=loan.name))

    @http.route('/my/hr/loans/new', type='http', auth='user', website=True, methods=['POST'])
    def om_hr_loan_new(self, **post):
        employee = self._om_employee()
        try:
            loan_type = request.env['om.hr.loan.type'].sudo().browse(int(post.get('type_id') or 0)).exists()
            # only the types the form offers: shared, or of the company of the employee
            if not loan_type or loan_type.company_id not in (employee.company_id, request.env['res.company']):
                raise UserError(request.env._('Choose a type of loan.'))
            values = {
                'employee_id': employee.id,
                'type_id': loan_type.id,
                'amount': float(post.get('amount') or 0),
                'installment_count': 1 if loan_type.is_advance else int(post.get('installment_count') or 1),
                'reason': post.get('reason') or False,
            }
            if post.get('date_start'):
                values['date_start'] = fields.Date.to_date(post['date_start'] + '-01'
                                                           if len(post['date_start']) == 7 else post['date_start'])
            with request.env.cr.savepoint():
                loan = request.env['om.hr.loan'].sudo().create(values)
                loan.action_submit()
        except (UserError, ValidationError, ValueError) as error:
            return self._om_loan_page(error=str(error.args[0] if error.args else error), form=post)
        return request.redirect('/my/hr/loans/%s' % loan.id)
