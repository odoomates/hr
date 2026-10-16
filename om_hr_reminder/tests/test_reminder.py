from datetime import date

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.om_hr_reminder.models.hr_employee import next_yearly


@tagged('post_install', '-at_install')
class TestReminder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager_user = new_test_user(cls.env, 'om_reminder_manager', groups='base.group_user')
        cls.hr_user = new_test_user(cls.env, 'om_reminder_hr', groups='base.group_user,hr.group_hr_user')
        cls.colleague_user = new_test_user(cls.env, 'om_reminder_colleague', groups='base.group_user')
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': 'Reminder Manager', 'user_id': cls.manager_user.id})
        Employee.create({'name': 'Reminder Colleague', 'user_id': cls.colleague_user.id})

    def employee(self, **values):
        return self.env['hr.employee'].create({
            'name': 'Reminded Employee', 'parent_id': self.manager.id, 'birthday': date(1990, 6, 20),
            'birthday_public_display': True, 'date_version': date(2020, 6, 25),
            'contract_date_start': date(2020, 6, 25), **values})

    def test_next_yearly(self):
        self.assertEqual(next_yearly(date(1990, 6, 20), date(2026, 6, 1)), date(2026, 6, 20))
        self.assertEqual(next_yearly(date(1990, 6, 20), date(2026, 6, 21)), date(2027, 6, 20), 'passed: next year')
        self.assertEqual(next_yearly(date(1990, 6, 20), date(2026, 6, 20)), date(2026, 6, 20), 'today counts')
        self.assertEqual(next_yearly(date(1992, 2, 29), date(2026, 1, 1)), date(2026, 2, 28), 'not a leap year')
        self.assertEqual(next_yearly(date(1992, 2, 29), date(2028, 1, 1)), date(2028, 2, 29))
        self.assertEqual(next_yearly(date(2026, 3, 1), date(2026, 1, 1), after=date(2026, 3, 1)), date(2027, 3, 1),
                         'an anniversary comes a year after the start')

    @freeze_time('2026-06-01')
    def test_dates_on_the_employee(self):
        employee = self.employee(trial_date_end=date(2026, 6, 30))
        self.assertEqual(employee.next_birthday, date(2026, 6, 20))
        self.assertEqual((employee.next_anniversary, employee.service_years), (date(2026, 6, 25), 6))
        self.assertEqual(employee.probation_end, date(2026, 6, 30))
        employee.birthday_public_display = False
        self.assertFalse(employee.next_birthday, 'a birthday not shown is not reminded')
        with freeze_time('2026-06-26'):
            self.env['hr.employee']._cron_update_reminder_dates()
            self.assertEqual((employee.next_anniversary, employee.service_years), (date(2027, 6, 25), 7))

    @freeze_time('2026-06-01')
    def test_reminders(self):
        employee = self.employee()
        employee.version_id.hr_responsible_id = self.hr_user
        employee._remind('birthday')
        self.assertEqual(employee.activity_ids.user_id, self.manager_user)
        employee.activity_ids.unlink()
        employee._remind('anniversary')
        self.assertEqual(employee.activity_ids.user_id, self.manager_user | self.hr_user)
        self.assertIn('6 years of service', employee.activity_ids[0].summary)

    @freeze_time('2026-06-01')
    def test_ready_made_rules(self):
        employee = self.employee()
        for xmlid in ('automation_birthday', 'automation_anniversary', 'automation_probation'):
            self.assertTrue(self.env.ref('om_hr_reminder.' + xmlid).active)
        action = self.env.ref('om_hr_reminder.action_birthday')
        action.with_context(active_model='hr.employee', active_ids=employee.ids, active_id=employee.id).run()
        self.assertEqual(employee.activity_ids.summary, 'Birthday of Reminded Employee')

    def test_celebrations_for_every_employee(self):
        today = date.today()
        employee = self.employee(date_version=today - relativedelta(years=3),
                                 contract_date_start=today - relativedelta(years=3))
        action = self.env.ref('om_hr_reminder.hr_employee_public_action_celebrations')
        domain = [
            '|',
            '&', ('next_birthday', '>=', today + relativedelta(day=1)),
            ('next_birthday', '<=', today + relativedelta(day=31)),
            '&', ('next_anniversary', '>=', today + relativedelta(day=1)),
            ('next_anniversary', '<=', today + relativedelta(day=31)),
        ]
        self.assertIn('next_anniversary', action.domain)
        # the public employees are a view of the database: what is written is flushed first
        self.env.flush_all()
        found = self.env['hr.employee.public'].with_user(self.colleague_user).search(domain)
        self.assertIn(employee.id, found.ids, 'a plain employee sees the anniversaries of the month')
