from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestDocumentBoardTour(HttpCase):

    def test_document_board(self):
        employee = self.env['hr.employee'].create({'name': 'Board Holder'})
        self.env['om.document'].create({
            'res_model': 'hr.employee', 'res_id': employee.id, 'number': 'P-1',
            'type_id': self.env.ref('om_hr_document.document_type_passport').id,
            'date_expiry': fields.Date.today() + timedelta(days=20),
        })
        self.start_tour(f'/odoo/employees/{employee.id}', 'om_hr_document_board', login='admin')
