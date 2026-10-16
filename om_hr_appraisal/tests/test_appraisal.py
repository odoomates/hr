from datetime import date

from freezegun import freeze_time

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
@freeze_time('2026-06-01')
class TestAppraisal(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_user = new_test_user(cls.env, 'om_appr_employee', groups='base.group_user')
        cls.manager_user = new_test_user(cls.env, 'om_appr_manager', groups='base.group_user')
        cls.other_user = new_test_user(cls.env, 'om_appr_other', groups='base.group_user')
        cls.hr_user = new_test_user(cls.env, 'om_appr_hr', groups='base.group_user,hr.group_hr_user')
        cls.department = cls.env['hr.department'].create({'name': 'Appraised Department'})
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': 'Appr Manager', 'user_id': cls.manager_user.id})
        cls.employee = Employee.create({
            'name': 'Appr Employee', 'user_id': cls.employee_user.id, 'parent_id': cls.manager.id,
            'department_id': cls.department.id, 'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1)})
        cls.other = Employee.create({'name': 'Appr Other', 'user_id': cls.other_user.id})
        cls.rating = cls.env.ref('om_hr_appraisal.rating_meets')

    def new_appraisal(self, **values):
        return self.env['hr.appraisal'].with_user(self.hr_user).create({
            'employee_id': self.employee.id, **values})

    def test_hr_responsible_reviews_without_a_manager_user(self):
        """ With no manager user, the HR responsible of the contract gets the review and may complete it, without
            being an HR officer. """
        responsible = new_test_user(self.env, 'om_appr_responsible', groups='base.group_user')
        no_user_manager = self.env['hr.employee'].create({'name': 'Appr Manager Without User'})
        self.employee.parent_id = no_user_manager
        self.employee.version_id.hr_responsible_id = responsible
        appraisal = self.new_appraisal()
        appraisal.with_user(self.hr_user).action_start()
        appraisal.with_user(self.employee_user).action_submit_self()
        self.assertEqual(appraisal.activity_ids.user_id, responsible, 'the review goes to the HR responsible')
        as_responsible = appraisal.with_user(responsible)
        self.assertIn('manager', as_responsible._roles())
        as_responsible.write({'rating_id': self.rating.id, 'manager_feedback': '<p>Solid year.</p>'})
        as_responsible.action_done()
        self.assertEqual(appraisal.state, 'done')
        with self.assertRaises(AccessError):
            appraisal.with_user(self.other_user).read(['name'])

    def test_flow_and_who_reads_what(self):
        appraisal = self.new_appraisal()
        self.assertEqual(appraisal.manager_id, self.manager)
        self.assertIn('My work', appraisal.employee_feedback, 'started from the default template')
        as_employee = appraisal.with_user(self.employee_user)
        as_manager = appraisal.with_user(self.manager_user)

        as_manager.action_start()
        self.assertEqual(appraisal.state, 'self')
        self.assertEqual(appraisal.activity_ids.user_id, self.employee_user)

        as_employee.employee_feedback = '<p>I closed the books on time.</p>'
        as_manager.manager_feedback = '<p>Private notes while waiting.</p>'
        as_employee.invalidate_recordset()
        as_manager.invalidate_recordset()
        self.assertFalse(as_manager.employee_feedback, 'the manager waits for the submission')
        self.assertFalse(as_employee.manager_feedback, 'the employee waits for the end')
        with self.assertRaises(UserError):
            as_employee.action_done()

        as_employee.action_submit_self()
        self.assertEqual(appraisal.state, 'review')
        self.assertEqual(appraisal.activity_ids.user_id, self.manager_user)
        as_manager.invalidate_recordset()
        self.assertIn('closed the books', as_manager.employee_feedback)
        with self.assertRaises(AccessError):
            as_employee.employee_feedback = '<p>Changed after submitting</p>'
        with self.assertRaises(AccessError):
            as_employee.rating_id = self.rating

        with self.assertRaises(UserError):
            as_manager.action_done()
        as_manager.write({'rating_id': self.rating.id, 'manager_feedback': '<p>Great year.</p>'})
        as_manager.action_done()
        self.assertEqual((appraisal.state, appraisal.date_done), ('done', date(2026, 6, 1)))
        self.assertFalse(appraisal.activity_ids)
        as_employee.invalidate_recordset()
        self.assertIn('Great year', as_employee.manager_feedback)
        with self.assertRaises(AccessError):
            as_manager.manager_feedback = '<p>Rewritten</p>'

    def test_feedback_hidden_through_the_api(self):
        appraisal = self.new_appraisal(manager_feedback='<p>Secret</p>')
        with self.assertRaises(AccessError):
            appraisal.with_user(self.employee_user).read(['manager_feedback_html'])
        self.assertFalse(appraisal.with_user(self.employee_user).read(['manager_feedback'])[0]['manager_feedback'])
        with self.assertRaises(AccessError):
            appraisal.with_user(self.other_user).read(['name'])

    def test_probation_without_self_assessment(self):
        appraisal = self.new_appraisal(kind='probation')
        appraisal.action_start()
        self.assertEqual(appraisal.state, 'review')
        self.assertEqual(appraisal.name, 'Probation Review of Appr Employee')

    def test_cycle(self):
        cycle = self.env['hr.appraisal.cycle'].with_user(self.hr_user).create({
            'name': 'Annual 2026', 'date_start': date(2025, 6, 1), 'date_end': date(2026, 5, 31),
            'date_deadline': date(2026, 6, 30), 'department_ids': [self.department.id],
            'employee_ids': [self.other.id]})
        cycle.action_generate()
        self.assertEqual(cycle.state, 'running')
        self.assertEqual(cycle.appraisal_ids.employee_id, self.employee | self.other)
        self.assertEqual(set(cycle.appraisal_ids.mapped('state')), {'self'})
        self.assertEqual(cycle.appraisal_ids.mapped('date_deadline'), [date(2026, 6, 30)] * 2)
        cycle.action_generate()
        self.assertEqual(len(cycle.appraisal_ids), 2, 'once per employee')

    def test_planned_probation_review(self):
        self.employee.version_id.trial_date_end = date(2026, 6, 10)
        Appraisal = self.env['hr.appraisal']
        Appraisal._cron_plan_appraisals()
        probation = Appraisal.search([('employee_id', '=', self.employee.id), ('kind', '=', 'probation')])
        self.assertEqual((probation.state, probation.date_deadline), ('review', date(2026, 6, 10)))
        self.assertEqual(probation.activity_ids.user_id, self.manager_user)
        Appraisal._cron_plan_appraisals()
        self.assertEqual(Appraisal.search_count([('employee_id', '=', self.employee.id),
                                                 ('kind', '=', 'probation')]), 1)

    def test_planned_regular_appraisals(self):
        company = self.employee.company_id
        company.write({'appraisal_first_months': 6, 'appraisal_interval_months': 12,
                       'appraisal_lead_days': 30, 'appraisal_probation': False})
        Appraisal = self.env['hr.appraisal']
        self.assertEqual(self.employee._next_appraisal_date(), date(2025, 7, 1))
        Appraisal._cron_plan_appraisals()
        appraisal = Appraisal.search([('employee_id', '=', self.employee.id)])
        self.assertEqual((len(appraisal), appraisal.state), (1, 'self'))
        self.assertEqual(appraisal.date_deadline, date(2026, 6, 1), 'overdue: due today')
        Appraisal._cron_plan_appraisals()
        self.assertEqual(Appraisal.search_count([('employee_id', '=', self.employee.id)]), 1, 'one open at a time')

        appraisal.sudo().write({'state': 'done', 'date_done': date(2026, 6, 1)})
        self.assertEqual(self.employee._next_appraisal_date(), date(2027, 6, 1))
        Appraisal._cron_plan_appraisals()
        self.assertEqual(Appraisal.search_count([('employee_id', '=', self.employee.id)]), 1, 'not due yet')
        with freeze_time('2027-05-10'):
            Appraisal._cron_plan_appraisals()
            self.assertEqual(Appraisal.search_count([('employee_id', '=', self.employee.id)]), 2)

    def test_new_contract_version(self):
        appraisal = self.new_appraisal()
        appraisal.sudo().write({'state': 'done', 'date_done': date(2026, 6, 1)})
        with self.assertRaises(UserError):
            appraisal.with_user(self.manager_user).action_new_contract_version()
        action = appraisal.with_user(self.hr_user).action_new_contract_version()
        wizard = self.env['hr.appraisal.version'].with_user(self.hr_user).with_context(**action['context']).create({})
        self.assertEqual(wizard.date_version, date(2026, 7, 1))
        result = wizard.action_create()
        version = self.env['hr.version'].browse(result['context']['version_id'])
        self.assertEqual((version.employee_id, version.date_version), (self.employee, date(2026, 7, 1)))
        self.assertEqual(result['res_model'], 'hr.employee')

    def test_goals(self):
        goal = self.env['hr.appraisal.goal'].with_user(self.manager_user).create({
            'name': 'Automate the bank reconciliation', 'employee_id': self.employee.id,
            'date_deadline': date(2026, 12, 31)})
        goal.with_user(self.employee_user).progress = 60
        with self.assertRaises(AccessError):
            goal.with_user(self.employee_user).name = 'Something easier'
        goal.with_user(self.employee_user).progress = 100
        self.assertTrue(goal.is_done)
        with self.assertRaises(AccessError):
            goal.with_user(self.other_user).read(['name'])
