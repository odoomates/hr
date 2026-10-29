from datetime import date

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMonthlyBatch(TransactionCase):
    """ With the monthly batch on, the batch of the month is created for the company from its day of the month,
        with the payslips of the employees under contract in draft. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Monthly Batch Company'})
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))
        if 'journal_id' in cls.env['hr.payslip.run']._fields:
            # payroll accounting is installed: a batch needs the salary journal of its company
            cls.env['account.journal'].create({
                'name': 'Monthly Salaries', 'code': 'MSAL', 'type': 'general', 'company_id': cls.company.id})
        cls.calendar = cls.env['resource.calendar'].create({'name': 'Monthly 40h', 'company_id': cls.company.id})
        cls.structure = cls.env['hr.payroll.structure'].create({
            'name': 'Monthly Structure', 'code': 'MONTHLYTEST', 'parent_id': False,
            'rule_ids': [Command.set((
                cls.env.ref('om_hr_payroll.hr_rule_basic') | cls.env.ref('om_hr_payroll.hr_rule_net')
            ).ids)],
        })
        cls.paid = cls._employee('Paid Employee', struct_id=cls.structure.id)
        cls.no_structure = cls._employee('Employee Without Structure')
        cls.no_contract = cls.env['hr.employee'].create({
            'name': 'Employee Without Contract', 'company_id': cls.company.id,
            'resource_calendar_id': cls.calendar.id})

    @classmethod
    def _employee(cls, name, **values):
        return cls.env['hr.employee'].create({
            'name': name, 'company_id': cls.company.id, 'resource_calendar_id': cls.calendar.id, 'tz': 'UTC',
            'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1), 'wage': 3000.0,
            **values,
        })

    def _batches(self):
        return self.env['hr.payslip.run'].search([('company_id', '=', self.company.id), ('om_monthly', '=', True)])

    def test_off_creates_nothing(self):
        with freeze_time('2026-06-25'):
            self.env['hr.payslip.run']._cron_monthly_batch()
        self.assertFalse(self._batches())

    def test_batch_of_the_month_from_its_day(self):
        self.company.write({'om_payroll_monthly_batch': True, 'om_payroll_monthly_batch_day': 25})
        with freeze_time('2026-06-24'):
            self.env['hr.payslip.run']._cron_monthly_batch()
        self.assertFalse(self._batches(), 'not before the day of the month')

        with freeze_time('2026-06-25'):
            self.env['hr.payslip.run']._cron_monthly_batch()
        run = self._batches()
        self.assertEqual(len(run), 1)
        self.assertEqual((run.date_start, run.date_end), (date(2026, 6, 1), date(2026, 6, 30)))
        self.assertEqual(run.state, 'draft')
        self.assertEqual(run.slip_ids.employee_id, self.paid, 'the employees under contract with a structure')
        self.assertEqual(run.slip_ids.state, 'draft', 'left to check and confirm')
        self.assertTrue(run.slip_ids.line_ids, 'the payslips are computed')
        message = run.message_ids[0].body
        self.assertIn('1 payslips in draft', message)
        self.assertIn(self.no_structure.name, message, 'the employees left out are named')
        self.assertNotIn(self.no_contract.name, message)

        with freeze_time('2026-06-28'):
            self.env['hr.payslip.run']._cron_monthly_batch()
        self.assertEqual(self._batches(), run, 'once a month')

        with freeze_time('2026-07-25'):
            self.env['hr.payslip.run']._cron_monthly_batch()
        self.assertEqual(len(self._batches()), 2, 'and again the next month')

    def test_day_beyond_a_short_month(self):
        """ A batch set on the 31st is created on the last day of a shorter month. """
        self.company.write({'om_payroll_monthly_batch': True, 'om_payroll_monthly_batch_day': 31})
        run = self.env['hr.payslip.run']._create_monthly_batch(self.company, today=date(2026, 6, 29))
        self.assertFalse(run)
        run = self.env['hr.payslip.run']._create_monthly_batch(self.company, today=date(2026, 6, 30))
        self.assertEqual(run.date_start, date(2026, 6, 1))

    def test_day_of_the_month(self):
        with self.assertRaises(ValidationError):
            self.company.om_payroll_monthly_batch_day = 32
