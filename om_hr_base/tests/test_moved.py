from odoo.tests import TransactionCase, tagged

from odoo.addons.om_hr_base.moved import FROM_PAYROLL, take_over


@tagged('post_install', '-at_install')
class TestMoved(TransactionCase):
    """ The records om_hr_payroll used to own are owned by om_hr_base, with the same database id. """

    def _xmlid(self, module, name):
        self.env.cr.execute("SELECT res_id FROM ir_model_data WHERE module = %s AND name = %s", [module, name])
        row = self.env.cr.fetchone()
        return row and row[0]

    def test_owned_by_base(self):
        for name in FROM_PAYROLL:
            self.assertTrue(self._xmlid('om_hr_base', name), name)
            self.assertFalse(self._xmlid('om_hr_payroll', name), name)

    def test_take_over(self):
        partner = self.env['res.partner'].create({'name': 'Moved'})
        self.env['ir.model.data'].create({
            'module': 'om_hr_payroll', 'name': 'om_test_moved', 'model': 'res.partner', 'res_id': partner.id})

        self.assertEqual(take_over(self.env.cr, ('om_test_moved',)), ['om_test_moved'])
        self.assertEqual(self._xmlid('om_hr_base', 'om_test_moved'), partner.id)
        self.assertFalse(self._xmlid('om_hr_payroll', 'om_test_moved'))
        # again: nothing left to take over
        self.assertEqual(take_over(self.env.cr, ('om_test_moved',)), [])

    def test_already_owned(self):
        """ When om_hr_base already has the external id, the one of the source is left to its upgrade. """
        partners = self.env['res.partner'].create([{'name': 'Base'}, {'name': 'Payroll'}])
        for module, partner in zip(('om_hr_base', 'om_hr_payroll'), partners, strict=True):
            self.env['ir.model.data'].create({
                'module': module, 'name': 'om_test_both', 'model': 'res.partner', 'res_id': partner.id})

        self.assertEqual(take_over(self.env.cr, ('om_test_both',)), [])
        self.assertEqual(self._xmlid('om_hr_base', 'om_test_both'), partners[0].id)
        self.assertEqual(self._xmlid('om_hr_payroll', 'om_test_both'), partners[1].id)
