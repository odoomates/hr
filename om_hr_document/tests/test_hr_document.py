from datetime import date

from freezegun import freeze_time

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
@freeze_time('2026-06-01')
class TestHrDocument(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_user = new_test_user(cls.env, 'om_doc_employee', groups='base.group_user')
        cls.other_user = new_test_user(cls.env, 'om_doc_other', groups='base.group_user')
        cls.hr_user = new_test_user(cls.env, 'om_doc_hr', groups='base.group_user,hr.group_hr_user')
        cls.hr_responsible = new_test_user(cls.env, 'om_doc_hr_responsible',
                                           groups='base.group_user,hr.group_hr_user')
        Employee = cls.env['hr.employee']
        cls.employee = Employee.create({'name': 'Document Holder', 'user_id': cls.employee_user.id,
                                        'work_email': 'holder@example.com'})
        cls.other = Employee.create({'name': 'Other Holder', 'user_id': cls.other_user.id})
        cls.passport_type = cls.env.ref('om_hr_document.document_type_passport')
        cls.national_id_type = cls.env.ref('om_hr_document.document_type_national_id')

    def new_document(self, doc_type=None, employee=None, user=None, **values):
        return self.env['om.document'].with_user(user or self.hr_user).create({
            'res_model': 'hr.employee', 'res_id': (employee or self.employee).id,
            'type_id': (doc_type or self.passport_type).id, **values})

    def test_access(self):
        mine = self.new_document(number='P1', date_expiry=date(2030, 1, 1))
        theirs = self.new_document(employee=self.other, number='P2')
        Document = self.env['om.document']
        self.assertEqual(mine.employee_id, self.employee)
        self.assertEqual(Document.with_user(self.employee_user).search([]), mine, 'employees read their own')
        with self.assertRaises(AccessError):
            theirs.with_user(self.employee_user).read(['number'])
        with self.assertRaises(AccessError):
            mine.with_user(self.employee_user).write({'number': 'X'})
        with self.assertRaises(AccessError):
            self.new_document(user=self.employee_user)
        self.assertEqual(Document.with_user(self.hr_user).search([('id', 'in', (mine | theirs).ids)]), mine | theirs)

    def test_reminder_goes_to_the_hr_responsible(self):
        self.employee.version_id.hr_responsible_id = self.hr_responsible
        document = self.new_document(number='P1', date_expiry=date(2026, 6, 20))
        self.env['om.document']._cron_send_reminders()
        self.assertEqual(document.activity_ids.user_id, self.hr_responsible)

    def test_reminder_without_responsible_goes_to_hr_managers(self):
        self.employee.version_id.hr_responsible_id = False
        managers = self.env.ref('hr.group_hr_manager').all_user_ids.filtered(
            lambda user: self.employee.company_id in user.company_ids)
        document = self.new_document(number='P1', date_expiry=date(2026, 6, 20))
        self.assertEqual(document._get_responsible_users(), managers)

    def test_holder_is_the_work_contact(self):
        document = self.new_document(number='P1')
        self.assertEqual(document._get_holder_partner(), self.employee.work_contact_id)

    def test_numbers_copied_to_the_employee(self):
        self.new_document(number='P123')
        self.new_document(doc_type=self.national_id_type, number='ID456')
        self.assertEqual((self.employee.passport_id, self.employee.identification_id), ('P123', 'ID456'))

    def test_board_and_counts(self):
        self.new_document(number='P1', date_expiry=date(2026, 6, 10))
        data = self.env['om.document'].with_user(self.hr_user).om_board_data('hr.employee', self.employee.id)
        self.assertEqual(len(data['documents']), 1)
        self.assertIn(self.env.ref('om_hr_document.document_type_work_permit').id,
                      [missing['id'] for missing in data['missing']])
        self.assertTrue(data['can_edit'])
        self.employee.invalidate_recordset()
        self.assertEqual((self.employee.om_document_count, self.employee.om_document_alert_count), (1, 1))

    def test_documents_go_with_the_employee(self):
        document = self.new_document(number='P1')
        self.employee.with_context(active_test=False).unlink()
        self.assertFalse(document.exists())
