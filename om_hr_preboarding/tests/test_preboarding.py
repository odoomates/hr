from datetime import timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import HttpCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestPreboarding(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_user = new_test_user(cls.env, 'om_preboarding_hr', groups='base.group_user,hr.group_hr_user',
                                    email='hr@example.com')
        cls.company = cls.env.company
        Step = cls.env['hr.preboarding.step']
        Step.search([]).active = False
        cls.sales = cls.env['hr.department'].create({'name': 'Sales'})
        cls.step_details = Step.create({'name': 'Details', 'kind': 'details', 'sequence': 1})
        cls.step_emergency = Step.create({'name': 'Emergency', 'kind': 'emergency', 'sequence': 2})
        cls.step_bank = Step.create({'name': 'Bank', 'kind': 'bank', 'sequence': 3})
        cls.step_read = Step.create({'name': 'First Day', 'kind': 'read', 'sequence': 4,
                                     'description': '<p>Come at nine.</p>'})
        cls.step_sales = Step.create({'name': 'Sales Kit', 'kind': 'task', 'sequence': 5, 'audience': 'department',
                                      'department_ids': [Command.set(cls.sales.ids)]})
        cls.manager = cls.env['hr.employee'].create({'name': 'Mona Manager', 'work_email': 'mona@example.com'})
        cls.start = fields.Date.today() + timedelta(days=10)
        cls.new_hire = cls.env['hr.employee'].create({
            'name': 'Nina Newcomer', 'private_email': 'nina@example.com', 'parent_id': cls.manager.id,
            'contract_date_start': cls.start, 'date_version': cls.start})

    def start_preboarding(self, employee=None):
        action = (employee or self.new_hire).with_user(self.hr_user).action_start_preboarding()
        return self.env['hr.preboarding'].browse(action['res_id'])

    def line(self, preboarding, step):
        return preboarding.line_ids.filtered(lambda line: line.step_id == step)

    def test_start(self):
        preboarding = self.start_preboarding()
        self.assertEqual(preboarding.line_ids.step_id, self.step_details | self.step_emergency | self.step_bank
                         | self.step_read, 'the Sales step is only for Sales')
        self.assertEqual((preboarding.date_start, preboarding.buddy_id), (self.start, self.manager))
        self.assertTrue(self.new_hire.user_id.share, 'the new hire gets a portal user')
        self.assertTrue(self.env['mail.message'].search([
            ('model', '=', 'hr.preboarding'), ('res_id', '=', preboarding.id),
            ('partner_ids', 'in', self.new_hire.user_id.partner_id.ids)]), 'the new hire is welcomed')
        with self.assertRaises(UserError):
            self.start_preboarding()
        without_date = self.env['hr.employee'].create({'name': 'No Date', 'private_email': 'nodate@example.com'})
        without_date.version_id.contract_date_start = False
        with self.assertRaises(UserError):
            self.start_preboarding(without_date)
        with self.assertRaises(UserError):
            self.new_hire.with_user(new_test_user(self.env, 'om_preboarding_nobody')).action_start_preboarding()

    def test_review_details(self):
        preboarding = self.start_preboarding()
        details = self.line(preboarding, self.step_details)
        with self.assertRaises(UserError):
            details._submit({'birthday': 'not a date'})
        with self.assertRaises(UserError):
            details._submit({'marital': 'complicated'})
        details._submit({'private_city': ' Dubai ', 'birthday': '1995-03-04', 'marital': 'single',
                         'country_id': str(self.env.ref('base.ae').id), 'children': '0'})
        self.assertEqual(details.state, 'submitted')
        self.assertNotEqual(self.new_hire.private_city, 'Dubai', 'nothing is written before HR applies it')
        self.assertIn('Dubai', details.review_html)
        self.assertEqual(preboarding.to_review_count, 1)
        with self.assertRaises(UserError):
            details._submit({'private_city': 'Again'})

        send_back = self.env['hr.preboarding.send.back'].with_user(self.hr_user).create(
            {'line_id': details.id, 'note': 'Give your full address.'})
        send_back.action_send_back()
        self.assertEqual((details.state, details.review_note), ('returned', 'Give your full address.'))
        details._submit({'private_street': '1 Palm Road', 'private_city': 'Dubai', 'birthday': '1995-03-04'})
        details.with_user(self.hr_user).action_apply()
        self.assertEqual((self.new_hire.private_city, self.new_hire.private_street), ('Dubai', '1 Palm Road'))
        self.assertEqual(str(self.new_hire.birthday), '1995-03-04')
        with self.assertRaises(UserError):
            details.with_user(new_test_user(self.env, 'om_preboarding_user')).action_apply()

    def test_bank_and_completion(self):
        preboarding = self.start_preboarding()
        bank = self.line(preboarding, self.step_bank)
        with self.assertRaises(UserError):
            bank._submit({'bank_name': 'Gulf Bank'})
        bank._submit({'account_number': 'AE070331234567890123456', 'bank_name': 'Gulf Bank'})
        bank.with_user(self.hr_user).action_apply()
        account = self.new_hire.bank_account_ids
        # with Accounting, an IBAN is shown in groups of four: its sanitized number is the one given
        self.assertEqual((account.sanitized_account_number, account.partner_id), ('AE070331234567890123456',
                                                                                  self.new_hire.work_contact_id))
        self.line(preboarding, self.step_read)._submit()
        emergency = self.line(preboarding, self.step_emergency)
        emergency._submit({'emergency_contact': 'Omar', 'emergency_phone': '+971 50 000 0000'})
        emergency.with_user(self.hr_user).action_apply()
        self.assertEqual(preboarding.state, 'running')
        details = self.line(preboarding, self.step_details)
        details._submit({'private_city': 'Dubai'})
        details.with_user(self.hr_user).action_apply()
        self.assertEqual((preboarding.state, preboarding.progress), ('done', 100))
        self.assertEqual(self.new_hire.emergency_contact, 'Omar')

    def test_closes_on_the_first_day(self):
        preboarding = self.start_preboarding()
        Preboarding = self.env['hr.preboarding']
        Preboarding._cron_follow_up()
        self.assertEqual(preboarding.state, 'running')
        with freeze_time(self.start):
            Preboarding._cron_follow_up()
        self.assertEqual(preboarding.state, 'closed')
        with self.assertRaises(UserError):
            self.line(preboarding, self.step_read)._submit()

    def test_onboarding_plan(self):
        plan = self.env['mail.activity.plan'].create({
            'name': 'Onboarding', 'res_model': 'hr.employee',
            'template_ids': [Command.create({'summary': 'Prepare the laptop', 'responsible_type': 'other',
                                             'responsible_id': self.hr_user.id,
                                             'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id})],
        })
        self.company.preboarding_plan_id = plan
        self.start_preboarding()
        self.assertIn('Prepare the laptop', self.new_hire.activity_ids.mapped('summary'))

    def test_portal(self):
        preboarding = self.start_preboarding()
        user = self.new_hire.user_id
        user.password = 'om_preboarding_nina'
        self.authenticate(user.login, 'om_preboarding_nina')
        self.assertIn('/my/welcome', self.url_open('/my/hr').text)
        page = self.url_open('/my/welcome').text
        self.assertIn('Nina Newcomer', page)
        self.assertIn('Mona Manager', page, 'the buddy is shown')
        emergency = self.line(preboarding, self.step_emergency)
        self.assertIn('Emergency Contact', self.url_open('/my/welcome/%s' % emergency.id).text)
        self.url_open('/my/welcome/%s' % emergency.id, data={
            'csrf_token': self.csrf_token(), 'emergency_contact': 'Omar', 'emergency_phone': '123'})
        self.assertEqual((emergency.state, emergency.data['emergency_contact']), ('submitted', 'Omar'))
        response = self.url_open('/my/welcome/%s' % self.line(preboarding, self.step_details).id,
                                 data={'csrf_token': self.csrf_token(), 'birthday': 'nope'})
        self.assertIn('is not a date', response.text)

        other = self.env['hr.employee'].create({
            'name': 'Other Hire', 'private_email': 'other@example.com',
            'contract_date_start': self.start, 'date_version': self.start})
        theirs = self.start_preboarding(other)
        self.assertEqual(self.url_open('/my/welcome/%s' % theirs.line_ids[0].id).status_code, 404)
