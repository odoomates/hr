from datetime import date

from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestAsset(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_user = new_test_user(cls.env, 'om_asset_hr', groups='base.group_user,hr.group_hr_user')
        cls.employee_user = new_test_user(cls.env, 'om_asset_employee', groups='base.group_user')
        cls.other_user = new_test_user(cls.env, 'om_asset_other', groups='base.group_user')
        Employee = cls.env['hr.employee']
        cls.employee = Employee.create({'name': 'Asset Holder', 'user_id': cls.employee_user.id,
                                        'date_version': date(2026, 1, 1), 'contract_date_start': date(2026, 1, 1)})
        cls.other = Employee.create({'name': 'Asset Other', 'user_id': cls.other_user.id})
        cls.laptop = cls.env['maintenance.equipment'].create({
            'name': 'Laptop', 'serial_no': 'SN-OM-123', 'equipment_assign_to': 'employee'})

    def wizard(self, mode, **values):
        context = {'default_equipment_id': self.laptop.id, 'default_mode': mode}
        return self.env['hr.asset.wizard'].with_user(self.hr_user).with_context(context).create(values)

    def assign(self, employee=None):
        return self.wizard('assign', employee_id=(employee or self.employee).id, condition='new',
                           date=date(2026, 6, 1)).action_confirm()

    def test_assign_and_return(self):
        self.assertEqual(self.laptop.asset_state, 'available')
        action = self.assign()
        self.assertEqual((self.laptop.employee_id, self.laptop.asset_state), (self.employee, 'assigned'))
        assignment = self.laptop.assignment_ids
        self.assertEqual((assignment.state, assignment.condition_out, assignment.date_from),
                         ('assigned', 'new', date(2026, 6, 1)))
        self.assertEqual(action['res_model'], 'print.wizard', 'the handover form is offered')

        self.wizard('return', condition='good', date=date(2026, 9, 1)).action_confirm()
        self.assertFalse(self.laptop.employee_id)
        self.assertEqual((assignment.state, assignment.condition_in, assignment.date_to, assignment.received_by_id),
                         ('returned', 'good', date(2026, 9, 1), self.hr_user))

    def test_damaged_return_charge_and_repair(self):
        self.assign()
        self.wizard('return', condition='damaged', charge_amount=150.0, request_maintenance=True,
                    note='Cracked screen').action_confirm()
        assignment = self.laptop.assignment_ids
        self.assertEqual((assignment.condition_in, assignment.charge_amount), ('damaged', 150.0))
        self.assertIn('Cracked screen', assignment.note)
        self.assertEqual(self.laptop.maintenance_ids.name, 'Repair Laptop')

    def test_lost_and_found(self):
        self.assign()
        self.wizard('lost', charge_amount=900.0).action_confirm()
        assignment = self.laptop.assignment_ids
        self.assertEqual((assignment.state, assignment.charge_amount), ('lost', 900.0))
        self.assertEqual((self.laptop.asset_state, self.laptop.employee_id), ('lost', self.env['hr.employee']))
        with self.assertRaises(UserError):
            self.assign()
        self.laptop.action_found()
        self.assertEqual(self.laptop.asset_state, 'available')

    def test_direct_change_keeps_the_history(self):
        self.laptop.employee_id = self.employee
        self.laptop.employee_id = self.other
        history = self.laptop.assignment_ids.sorted('id')
        self.assertEqual(history.employee_id, self.employee | self.other)
        self.assertEqual(history.mapped('state'), ['returned', 'assigned'])

    def test_reassign_closes_the_previous_holder(self):
        self.assign()
        self.assign(self.other)
        self.assertEqual(self.laptop.assignment_ids.filtered(lambda a: a.state == 'assigned').employee_id,
                         self.other)

    def test_departure_unassign_is_logged(self):
        self.assign()
        departure = self.env['hr.employee.departure'].create({
            'employee_id': self.employee.id, 'departure_date': date(2026, 9, 30)})
        departure.action_register()
        self.assertFalse(self.laptop.employee_id)
        self.assertEqual(self.laptop.assignment_ids.state, 'returned')

    def test_employees_see_their_own(self):
        self.assign()
        Assignment = self.env['hr.asset.assignment']
        self.assertEqual(Assignment.with_user(self.employee_user).search([]), self.laptop.assignment_ids)
        self.assertFalse(Assignment.with_user(self.other_user).search([]))
        with self.assertRaises(AccessError):
            self.laptop.assignment_ids.with_user(self.employee_user).write({'note': 'mine now'})

    def test_handover_form(self):
        action = self.assign()
        wizard = Form(self.env['print.wizard'].with_user(self.hr_user).with_context(action['context'])).save()
        wizard.action_issue()
        issue = self.env['print.issue'].search([('res_model', '=', 'hr.asset.assignment')], limit=1)
        self.assertIn('SN-OM-123', issue.body_html)
        self.assertIn('Asset Holder', issue.body_html)
        self.assertIn('New', issue.body_html)
