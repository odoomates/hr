from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools.binary import BinaryBytes

from odoo.addons.om_sign.tests.common import SIGNATURE, blank_pdf


@tagged('post_install', '-at_install')
class TestHrSign(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_user = new_test_user(cls.env, 'om_hr_sign_officer', groups='base.group_user,hr.group_hr_user',
                                    email='officer@example.com')
        cls.user_a = new_test_user(cls.env, 'om_hr_sign_a', groups='base.group_user', email='a@example.com')
        cls.user_b = new_test_user(cls.env, 'om_hr_sign_b', groups='base.group_user', email='b@example.com')
        Department = cls.env['hr.department']
        cls.commercial = Department.create({'name': 'Commercial'})
        cls.sales = Department.create({'name': 'Sales', 'parent_id': cls.commercial.id})
        cls.operations = Department.create({'name': 'Operations'})
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': 'Mona Manager', 'work_email': 'mona@example.com'})
        cls.employee_a = Employee.create({
            'name': 'Adam Sales', 'user_id': cls.user_a.id, 'work_email': 'adam@example.com',
            'department_id': cls.sales.id, 'parent_id': cls.manager.id})
        cls.employee_b = Employee.create({
            'name': 'Bella Ops', 'user_id': cls.user_b.id, 'work_email': 'bella@example.com',
            'department_id': cls.operations.id})

    def policy(self, answer='acknowledge', content='text', **values):
        policy = self.env['hr.policy'].with_user(self.hr_user).create({
            'name': 'Code of Conduct', 'answer_type': answer, **values})
        action = policy.action_new_version()
        version = self.env['hr.policy.version'].with_user(self.hr_user).browse(action['res_id'])
        if content == 'pdf':
            version.write({'content_type': 'pdf', 'document_file': BinaryBytes(blank_pdf()),
                           'document_filename': 'conduct.pdf'})
        else:
            version.body = '<p>Be kind.</p>'
        return policy, version

    def assignment(self, version, employee):
        return version.assignment_ids.filtered(lambda assignment: assignment.employee_id in employee)

    # ------------------------------------------------------------------
    # Employees as signers
    # ------------------------------------------------------------------

    def test_employees_sign_prints(self):
        template = self.env['print.template'].create({
            'name': 'Contract', 'model_id': self.env['ir.model']._get_id('hr.employee'),
            'body_html': '<p>Contract of <t t-out="object.name"/></p>',
            'sign_role_ids': [
                Command.create({'sequence': 10, 'name': 'Employee', 'signer_type': 'field'}),
                Command.create({'sequence': 20, 'name': 'Manager', 'signer_type': 'field', 'field_path': 'parent_id'}),
            ],
        })
        issue = self.env['print.issue'].with_user(self.hr_user)._create_from_template(template, self.employee_a.ids)
        issue.action_issue()
        sign_request = self.env['sign.request'].with_user(self.hr_user)._create_for_issue(issue)
        self.assertEqual(sign_request.signer_ids.partner_id,
                         self.employee_a.work_contact_id | self.manager.work_contact_id)
        sign_request.action_send()
        self.assertEqual(self.employee_a.with_user(self.hr_user).sign_request_count, 1)
        self.assertEqual(self.manager.with_user(self.hr_user).sign_request_count, 1, 'the requests they sign')

    def test_request_signature_from_the_employee(self):
        action = self.employee_b.with_user(self.hr_user).action_request_signature()
        sign_request = self.env['sign.request'].browse(action['res_id'])
        self.assertEqual(sign_request.signer_ids.partner_id, self.employee_b.work_contact_id)
        self.assertEqual((sign_request.res_model, sign_request.res_id), ('hr.employee', self.employee_b.id))
        # HR reads the requests about the employees, even sent by somebody else
        other = new_test_user(self.env, 'om_hr_sign_other_officer', groups='base.group_user,hr.group_hr_user')
        self.assertEqual(sign_request.with_user(other).name, 'Bella Ops')

    # ------------------------------------------------------------------
    # Policies
    # ------------------------------------------------------------------

    def test_read_and_agree(self):
        policy, version = self.policy(audience='department', department_ids=[Command.set(self.commercial.ids)])
        self.assertEqual(policy.audience_count, 1, 'sub-departments included')
        version.action_publish()
        self.assertEqual(policy.version_id, version)
        assignment = self.assignment(version, self.employee_a)
        self.assertEqual(version.assignment_ids, assignment)
        self.assertEqual(assignment.date_due, fields.Date.today() + timedelta(days=14))
        self.assertTrue(self.env['mail.message'].search([
            ('model', '=', 'hr.policy'), ('res_id', '=', policy.id),
            ('partner_ids', 'in', self.employee_a.work_contact_id.ids)]), 'the employee is told')

        with self.assertRaises(UserError):
            assignment.with_user(self.user_b).action_acknowledge()
        mine = assignment.with_user(self.user_a)
        self.assertIn('Be kind', mine.body)
        mine.action_acknowledge()
        self.assertEqual((assignment.state, assignment.done_by_id), ('done', self.user_a))
        self.assertEqual((policy.done_count, policy.done_rate), (1, 100.0))
        with self.assertRaises(UserError):
            mine.action_acknowledge()
        with self.assertRaises(UserError):
            assignment.with_user(self.hr_user).write({'state': 'pending'})

    def test_new_version_asks_again(self):
        policy, first = self.policy()
        first.action_publish()
        self.assignment(first, self.employee_a).with_user(self.user_a).action_acknowledge()
        with self.assertRaises(UserError):
            first.with_user(self.hr_user).body = '<p>Changed</p>'
        second = self.env['hr.policy.version'].browse(policy.with_user(self.hr_user).action_new_version()['res_id'])
        self.assertEqual(second.number, 2)
        self.assertIn('Be kind', second.body, 'the text of the current version is copied')
        with self.assertRaises(UserError):
            policy.action_new_version()
        second.action_publish()
        self.assertEqual((first.state, second.state), ('superseded', 'published'))
        self.assertEqual(self.assignment(first, self.employee_a).state, 'done', 'the past answers stay')
        self.assertEqual(self.assignment(first, self.employee_b).state, 'cancelled')
        self.assertEqual(set(self.assignment(second, self.employee_a | self.employee_b).mapped('state')), {'pending'})

    def test_signed_policy(self):
        _policy, version = self.policy(answer='sign', content='pdf', audience='employee',
                                      employee_ids=[Command.set((self.employee_a | self.employee_b).ids)])
        version.action_publish()
        assignment = self.assignment(version, self.employee_a)
        sign_request = assignment.sign_request_id
        self.assertEqual(sign_request.state, 'sent')
        self.assertEqual(sign_request.signer_ids.partner_id, self.employee_a.work_contact_id)
        self.assertEqual(sign_request.date_deadline, assignment.date_due)
        action = assignment.with_user(self.user_a).action_sign()
        self.assertIn('/sign/%s/' % sign_request.signer_ids.id, action['url'])
        with self.assertRaises(UserError):
            assignment.with_user(self.user_b).action_sign()

        sign_request.signer_ids.sudo()._sign('Adam Sales', SIGNATURE)
        self.assertEqual(assignment.state, 'done')

        other = self.assignment(version, self.employee_b)
        other.sign_request_id.signer_ids.sudo()._decline('I disagree')
        self.assertEqual(other.state, 'declined')
        other.with_user(self.hr_user).action_send_again()
        self.assertEqual((other.state, other.sign_request_id.state), ('pending', 'sent'))
        self.assertNotEqual(other.sign_request_id, sign_request)

    def test_signed_text_policy(self):
        _policy, version = self.policy(answer='sign')
        # the tests render the reports as HTML, which cannot be signed: the PDF of the text is given here
        with patch.object(type(version), '_get_pdf', return_value=blank_pdf()):
            version.action_publish()
        self.assertEqual(set(version.assignment_ids.sign_request_id.mapped('state')), {'sent'})

    def test_no_email(self):
        self.employee_b.work_contact_id.email = False
        _policy, version = self.policy(answer='sign', content='pdf')
        version.action_publish()
        assignment = self.assignment(version, self.employee_b)
        self.assertFalse(assignment.sign_request_id)
        self.assertIn('no work email', assignment.problem)

    def test_new_employees_are_asked(self):
        policy, version = self.policy(audience='department', department_ids=[Command.set(self.sales.ids)])
        version.action_publish()
        joiner = self.env['hr.employee'].create({'name': 'New Sales', 'department_id': self.sales.id})
        self.assertTrue(self.assignment(version, joiner))
        self.employee_b.department_id = self.sales
        self.assertTrue(self.assignment(version, self.employee_b), 'moved into the audience')
        self.employee_b.department_id = self.operations
        self.employee_b.department_id = self.sales
        self.assertEqual(len(self.assignment(version, self.employee_b)), 1, 'asked once')

        policy.assign_new = False
        late = self.env['hr.employee'].create({'name': 'Late Sales', 'department_id': self.sales.id})
        self.assertFalse(self.assignment(version, late))

        joiner.active = False
        self.assertEqual(self.assignment(version, joiner).state, 'cancelled')

    def test_reminders(self):
        _policy, version = self.policy(remind_days=7)
        version.action_publish()
        assignment = self.assignment(version, self.employee_a)
        Assignment = self.env['hr.policy.assignment']
        with freeze_time(fields.Datetime.now() + timedelta(days=6)):
            Assignment._cron_remind()
        self.assertFalse(assignment.date_reminded)
        with freeze_time(fields.Datetime.now() + timedelta(days=7, hours=1)):
            Assignment._cron_remind()
        self.assertTrue(assignment.date_reminded)
        self.assertTrue(Assignment.search([('id', '=', assignment.id), ('is_overdue', '=', False)]))
        with freeze_time(fields.Date.today() + timedelta(days=15)):
            self.assertTrue(Assignment.search([('id', '=', assignment.id), ('is_overdue', '=', True)]))

    def test_access(self):
        policy, version = self.policy(audience='employee', employee_ids=[Command.set(self.employee_a.ids)])
        version.action_publish()
        other_policy, other_version = self.policy(audience='employee', employee_ids=[Command.set(self.employee_b.ids)])
        other_version.action_publish()
        Assignment = self.env['hr.policy.assignment']
        self.assertEqual(Assignment.with_user(self.user_a).search([]), self.assignment(version, self.employee_a))
        self.assertEqual(policy.with_user(self.user_a).name, 'Code of Conduct')
        with self.assertRaises(AccessError):
            other_policy.with_user(self.user_a).read(['name'])
        with self.assertRaises(AccessError):
            self.assignment(other_version, self.employee_b).with_user(self.user_a).read(['state'])
        with self.assertRaises(AccessError):
            self.env['hr.policy'].with_user(self.user_a).create({'name': 'Mine'})
