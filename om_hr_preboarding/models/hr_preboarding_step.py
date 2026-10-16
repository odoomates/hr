from odoo import api, fields, models

# what the new hire fills in, by kind of step: written on the employee once HR applies it
DETAIL_FIELDS = {
    'details': ['private_street', 'private_street2', 'private_zip', 'private_city', 'private_country_id',
                'private_phone', 'private_email', 'birthday', 'place_of_birth', 'country_of_birth', 'country_id',
                'sex', 'marital', 'spouse_complete_name', 'spouse_birthdate', 'children'],
    'emergency': ['emergency_contact', 'emergency_phone'],
    'ids': ['identification_id', 'passport_id', 'visa_no', 'permit_no'],
}
# the bank account is created on the work contact of the employee
BANK_FIELDS = ['account_number', 'bank_name', 'bank_bic', 'holder_name']


class HrPreboardingStep(models.Model):
    """ A step of the pre-boarding of the new hires of a company, e.g. give the emergency contact, or read the
    first-day information; asked to all of them, or to some departments, job positions or tags. """
    _name = 'hr.preboarding.step'
    _inherit = ['hr.audience.mixin']
    _description = 'Pre-boarding Step'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    kind = fields.Selection([
        ('details', 'Personal Details'),
        ('emergency', 'Emergency Contact'),
        ('bank', 'Bank Account'),
        ('ids', 'ID Numbers'),
        ('read', 'Read'),
        ('task', 'Task'),
    ], required=True, default='task',
        help='Personal Details, Emergency Contact, Bank Account and ID Numbers: the new hire fills a form that HR '
             'reviews before it is written on the employee. Read: a page to read. Task: something to do, confirmed '
             'by the new hire.')
    description = fields.Html(translate=True, help='Shown to the new hire on the step.')

    @api.model
    def _review_kinds(self):
        """ :return: the kinds whose answer HR reviews before applying it """
        return ['details', 'emergency', 'bank', 'ids']

    @api.model
    def _auto_kinds(self):
        """ Hook: the kinds done by themselves once other records are, e.g. a document uploaded """
        return []

    def _line_values(self):
        """ Hook: :return: the values of the step of a new hire made from this step """
        self.ensure_one()
        return {'step_id': self.id, 'name': self.name, 'sequence': self.sequence, 'kind': self.kind,
                'description': self.description}
