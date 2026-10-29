# -*- coding: utf-8 -*-

from odoo.addons.om_hr_payroll.tests.common import TestPayslipBase


class TestPayslipFlow(TestPayslipBase):

    def test_00_payslip_flow(self):
        """ Compute, confirm and refund a payslip, generate a batch and print the reports. """
        richard_payslip = self._new_payslip()
        richard_payslip.input_line_ids.filtered(lambda line: line.code == 'SALEURO').amount = 5.0
        self.assertEqual(richard_payslip.state, 'draft')

        richard_payslip.compute_sheet()
        totals = self._totals(richard_payslip)
        self.assertEqual(totals['BASIC'], 5000.0)
        self.assertEqual(totals['HRA'], 2000.0)
        self.assertEqual(totals['SALECOMM'], 5.0)
        self.assertEqual(totals['GROSS'], 7805.0)
        self.assertEqual(totals['NET'], 7805.0 - 200.0 - 625.0)

        richard_payslip.action_payslip_done()
        self.assertEqual(richard_payslip.state, 'done')

        richard_payslip.refund_sheet()
        payslip_refund = self.env['hr.payslip'].search([
            ('name', '=', 'Refund: ' + richard_payslip.name), ('credit_note', '=', True)])
        self.assertTrue(payslip_refund, 'Payslip not refunded!')
        self.assertEqual(payslip_refund.state, 'done')

        # a batch generates the payslips of the employees chosen in its wizard
        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': '2011-10-01',
            'date_end': '2011-10-31',
            'name': 'October Payslips',
        })
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.richard_emp.id)],
        })
        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()
        self.assertEqual(payslip_run.slip_ids.employee_id, self.richard_emp)
        self.assertEqual(self._totals(payslip_run.slip_ids)['BASIC'], 5000.0)

        # the reports of the payslip and of the contribution register
        self.env.ref('om_hr_payroll.action_report_payslip')._render_qweb_html(richard_payslip.ids)
        self.env.ref('om_hr_payroll.payslip_details_report')._render_qweb_html(richard_payslip.ids)
        register_wizard = self.env['payslip.lines.contribution.register'].create({
            'date_from': '2011-09-01',
            'date_to': '2011-09-30',
        })
        # the layout of the company is not chosen yet: print anyway
        action = register_wizard.with_context(
            active_ids=self.house_rent_register.ids, discard_logo_check=True).print_report()
        report = self.env.ref('om_hr_payroll.action_contribution_register').with_context(
            active_ids=self.house_rent_register.ids)
        html = report._render_qweb_html(self.house_rent_register.ids, data=action['data'])[0]
        self.assertIn(b'House Rent Allowance', html)
