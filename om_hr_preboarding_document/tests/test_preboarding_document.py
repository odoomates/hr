from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestPreboardingDocument(TransactionCase):

    def test_upload_step(self):
        hr_user = new_test_user(self.env, 'om_preboarding_doc_hr', groups='base.group_user,hr.group_hr_user')
        Step = self.env['hr.preboarding.step']
        Step.search([]).active = False
        passport = self.env.ref('om_hr_document.document_type_passport')
        step = Step.create({'name': 'Your passport', 'kind': 'document', 'document_type_id': passport.id})
        start = fields.Date.today() + timedelta(days=7)
        employee = self.env['hr.employee'].create({
            'name': 'Paul Passport', 'private_email': 'paul@example.com', 'contract_date_start': start,
            'date_version': start})
        action = employee.with_user(hr_user).action_start_preboarding()
        line = self.env['hr.preboarding'].browse(action['res_id']).line_ids
        self.assertEqual((line.step_id, line.document_type_id), (step, passport))
        document = line.document_id
        self.assertEqual((document.employee_id, document.type_id), (employee, passport),
                         'the passport waits in the documents of the employee')
        with self.assertRaises(UserError):
            line._submit()
        line.preboarding_id._refresh()
        self.assertEqual(line.state, 'todo')
        document.attachment_ids = [(0, 0, {'name': 'passport.pdf', 'raw': b'%PDF-1.4'})]
        self.env['hr.preboarding']._cron_follow_up()
        self.assertEqual((line.state, line.preboarding_id.state), ('done', 'done'))
