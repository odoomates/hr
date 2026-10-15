from datetime import date

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestAssetExit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_user = new_test_user(cls.env, 'om_asset_exit_hr', groups='base.group_user,hr.group_hr_user')
        cls.it_user = new_test_user(cls.env, 'om_asset_exit_it', groups='base.group_user')
        cls.env['om.hr.exit.checklist'].search([]).active = False
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Leaving Holder', 'date_version': date(2024, 1, 1), 'contract_date_start': date(2024, 1, 1)})
        Equipment = cls.env['maintenance.equipment']
        cls.laptop = Equipment.create({'name': 'Exit Laptop', 'serial_no': 'SN-EXIT-1',
                                       'technician_user_id': cls.it_user.id})
        cls.phone = Equipment.create({'name': 'Exit Phone', 'serial_no': 'SN-EXIT-2'})
        (cls.laptop | cls.phone).write({'employee_id': cls.employee.id})

    def asset_wizard(self, equipment, mode, **values):
        return self.env['om.hr.asset.wizard'].with_user(self.hr_user).with_context(
            default_equipment_id=equipment.id, default_mode=mode).create(values)

    def test_exit_cleared_by_returning_the_assets(self):
        exit_ = self.env['om.hr.exit'].create({
            'employee_id': self.employee.id, 'date_notice': date(2026, 6, 1), 'notice_days': 30})
        exit_.write({'state': 'approved', 'approval_state': 'approved'})
        exit_._create_clearance()
        lines = exit_.clearance_ids
        self.assertEqual(len(lines), 2)
        laptop_line = lines.filtered(lambda line: line.asset_assignment_id.equipment_id == self.laptop)
        self.assertEqual(laptop_line.name, 'Return: Exit Laptop/SN-EXIT-1')
        self.assertEqual(laptop_line.responsible_user_ids, self.it_user)
        self.assertFalse(exit_.is_cleared)

        with self.assertRaises(UserError):
            laptop_line.with_user(self.it_user).action_clear()
        with self.assertRaises(UserError):
            laptop_line.with_user(self.hr_user).action_not_needed()

        self.asset_wizard(self.laptop, 'return', condition='good').action_confirm()
        self.assertEqual((laptop_line.state, laptop_line.note), ('done', 'Asset returned'))
        self.asset_wizard(self.phone, 'lost').action_confirm()
        self.assertTrue(exit_.is_cleared)
        exit_.with_user(self.hr_user).action_done()
        self.assertEqual(exit_.state, 'done')
