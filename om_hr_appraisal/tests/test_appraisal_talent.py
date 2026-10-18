from datetime import date, datetime

from freezegun import freeze_time

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
@freeze_time('2026-06-01')
class TestAppraisalTalent(TransactionCase):
    """ Goal alignment, one-on-ones, the 9-box grid and the calibration sessions. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_user = new_test_user(cls.env, 'om_talent_employee', groups='base.group_user')
        cls.manager_user = new_test_user(cls.env, 'om_talent_manager', groups='base.group_user')
        cls.other_user = new_test_user(cls.env, 'om_talent_other', groups='base.group_user')
        cls.hr_user = new_test_user(cls.env, 'om_talent_hr', groups='base.group_user,hr.group_hr_user')
        Employee = cls.env['hr.employee']
        cls.manager = Employee.create({'name': 'Talent Manager', 'user_id': cls.manager_user.id})
        cls.department = cls.env['hr.department'].create({'name': 'Talent Department', 'manager_id': cls.manager.id})
        cls.employee = Employee.create({
            'name': 'Talent Employee', 'user_id': cls.employee_user.id, 'parent_id': cls.manager.id,
            'department_id': cls.department.id})
        cls.colleague = Employee.create({
            'name': 'Talent Colleague', 'parent_id': cls.manager.id, 'department_id': cls.department.id})
        cls.other = Employee.create({'name': 'Talent Other', 'user_id': cls.other_user.id})
        cls.meets = cls.env.ref('om_hr_appraisal.rating_meets')
        cls.exceeds = cls.env.ref('om_hr_appraisal.rating_exceeds')

    # ------------------------------------------------------------------
    # Goal alignment
    # ------------------------------------------------------------------

    def test_goal_progress_rolls_up(self):
        Goal = self.env['hr.appraisal.goal'].with_user(self.hr_user)
        company_goal = Goal.create({'name': 'Grow 20%', 'level': 'company'})
        department_goal = Goal.with_user(self.manager_user).create({
            'name': 'Open two markets', 'level': 'department', 'department_id': self.department.id,
            'parent_id': company_goal.id})
        mine = Goal.with_user(self.manager_user).create({
            'name': 'Sign ten partners', 'employee_id': self.employee.id, 'parent_id': department_goal.id})
        theirs = Goal.with_user(self.manager_user).create({
            'name': 'Hire a team', 'employee_id': self.colleague.id, 'parent_id': department_goal.id})
        self.assertEqual(mine.department_id, self.department)

        mine.with_user(self.employee_user).progress = 80
        self.assertEqual(department_goal.progress, 40, 'The average of 80 and 0')
        self.assertEqual(company_goal.progress, 40)
        theirs.progress = 40
        self.assertEqual(department_goal.progress, 60)
        self.assertEqual(company_goal.progress, 60)
        with self.assertRaises(UserError):
            department_goal.with_user(self.manager_user).progress = 10

        theirs.unlink()
        self.assertEqual(department_goal.progress, 80)
        # an employee reads the goals of the company and of the department, and changes none of them
        company_goal.with_user(self.employee_user).read(['name', 'progress'])
        with self.assertRaises(AccessError):
            department_goal.with_user(self.employee_user).name = 'Changed'
        with self.assertRaises(UserError):
            company_goal.parent_id = mine  # a goal serving itself

    def test_goal_levels_need_their_owner(self):
        Goal = self.env['hr.appraisal.goal']
        with self.assertRaises(ValidationError):
            Goal.create({'name': 'Nobody', 'level': 'employee'})
        with self.assertRaises(ValidationError):
            Goal.create({'name': 'No department', 'level': 'department'})
        self.assertEqual(Goal.create({'name': 'The company', 'level': 'company'}).company_id, self.env.company)

    # ------------------------------------------------------------------
    # One-on-ones
    # ------------------------------------------------------------------

    def test_one_on_one_private_notes_and_actions(self):
        appraisal = self.env['hr.appraisal'].create({'employee_id': self.employee.id})
        meeting = self.env['hr.one.on.one'].with_user(self.manager_user).create({
            'employee_id': self.employee.id, 'date': datetime(2026, 6, 3, 9, 0), 'repeat_weeks': 2,
            'notes': '<p>Shared</p>', 'manager_note': '<p>Thinks of leaving</p>'})
        self.assertEqual(meeting.manager_id, self.manager)
        self.assertEqual(meeting.appraisal_id, appraisal, 'It prepares the open appraisal')

        as_employee = meeting.with_user(self.employee_user)
        self.assertFalse(as_employee.manager_note, 'The employee never reads the private notes')
        self.assertIn('Shared', as_employee.notes)
        as_employee.notes = '<p>Shared, and my point</p>'
        with self.assertRaises(AccessError):
            as_employee.manager_note = '<p>Mine now</p>'
        with self.assertRaises(AccessError):
            as_employee.date = datetime(2026, 6, 4, 9, 0)
        with self.assertRaises(AccessError):
            meeting.with_user(self.other_user).read(['notes'])
        self.assertIn('leaving', meeting.with_user(self.hr_user).manager_note)

        action = self.env['hr.one.on.one.action'].with_user(self.manager_user).create({
            'one_on_one_id': meeting.id, 'name': 'Book the training', 'user_id': self.employee_user.id,
            'date_deadline': date(2026, 6, 10)})
        self.assertEqual(meeting.activity_ids.user_id, self.employee_user)
        action.with_user(self.employee_user).done = True
        self.assertFalse(meeting.activity_ids, 'The to-do is done with the action')

        meeting.with_user(self.manager_user).action_done()
        following = self.env['hr.one.on.one'].search([
            ('employee_id', '=', self.employee.id), ('state', '=', 'planned')])
        self.assertEqual(following.date, datetime(2026, 6, 17, 9, 0), 'Planned two weeks later')
        self.assertFalse(following.notes)
        self.assertFalse(following.sudo().manager_note_html)
        self.assertEqual(appraisal.one_on_one_count, 2)
        with self.assertRaises(UserError):
            following.with_user(self.employee_user).action_done()

    # ------------------------------------------------------------------
    # 9-box and calibration
    # ------------------------------------------------------------------

    def _rated(self, employee, rating, potential):
        appraisal = self.env['hr.appraisal'].create({'employee_id': employee.id})
        appraisal.write({'rating_id': rating.id, 'potential': potential})
        return appraisal

    def test_nine_box_and_potential_privacy(self):
        appraisal = self.env['hr.appraisal'].with_user(self.hr_user).create({'employee_id': self.employee.id})
        appraisal.with_user(self.manager_user).write({'rating_id': self.exceeds.id, 'potential': 'high'})
        self.assertEqual(appraisal.sudo().potential_level, 'high')
        self.assertEqual(appraisal.sudo().box, '9')
        self.assertEqual(appraisal.with_user(self.manager_user).potential, 'high')
        self.assertFalse(appraisal.with_user(self.employee_user).potential, 'The employee never reads it')
        with self.assertRaises(AccessError):
            appraisal.with_user(self.employee_user).read(['potential_level'])
        with self.assertRaises(AccessError):
            appraisal.with_user(self.employee_user).potential = 'low'
        appraisal.rating_id = self.meets
        self.assertEqual(appraisal.sudo().box, '8', 'Medium performance, high potential')

    def test_calibration_adjusts_and_logs(self):
        appraisal = self._rated(self.employee, self.meets, 'medium')
        session = self.env['hr.appraisal.calibration'].with_user(self.hr_user).create({
            'name': 'Talent Calibration', 'appraisal_ids': [(4, appraisal.id)]})
        Adjust = self.env['hr.appraisal.calibration.adjust'].with_user(self.hr_user).with_context(
            appraisal_id=appraisal.id)
        with Form(Adjust.with_context(default_calibration_id=session.id)) as form:
            self.assertEqual((form.rating_id, form.potential), (self.meets, 'medium'))
            form.rating_id = self.exceeds
            form.reason = 'Led the migration alone'
        with self.assertRaises(UserError):
            form.record.action_apply()  # the session is not started

        session.action_start()
        form.record.action_apply()
        self.assertEqual(appraisal.rating_id, self.exceeds)
        self.assertEqual(appraisal.sudo().box, '6')
        log = session.log_ids
        self.assertEqual((log.what, log.old_value, log.new_value, log.user_id),
                         ('rating', self.meets.name, self.exceeds.name, self.hr_user))
        self.assertEqual(log.reason, 'Led the migration alone')
        with self.assertRaises(AccessError):
            session.with_user(self.manager_user).read(['name'])
