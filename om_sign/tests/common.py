import io

from odoo.tests import new_test_user
from odoo.tools.binary import BinaryBytes
from odoo.tools.pdf import PdfFileWriter

# a 1 x 1 PNG, as the signature pad sends it
SIGNATURE = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='


def blank_pdf():
    writer = PdfFileWriter()
    writer.add_blank_page(width=200, height=200)
    with io.BytesIO() as stream:
        writer.write(stream)
        return stream.getvalue()


class SignCommon:
    """ A template printed for contacts, signed by the contact and then a witness. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sender = new_test_user(cls.env, 'om_sign_sender', groups='base.group_user,om_sign.group_sign_user',
                                   email='sender@example.com')
        cls.outsider = new_test_user(cls.env, 'om_sign_outsider', groups='base.group_user',
                                     email='outsider@example.com')
        cls.customer = cls.env['res.partner'].create({'name': 'Acme Buyer', 'email': 'buyer@example.com'})
        cls.witness = cls.env['res.partner'].create({'name': 'Wanda Witness', 'email': 'witness@example.com'})
        cls.template = cls.env['print.template'].create({
            'name': 'Agreement',
            'model_id': cls.env['ir.model']._get_id('res.partner'),
            'subject': 'Agreement with {{ object.name }}',
            'body_html': '<p>We agree with <t t-out="object.name"/>.</p>',
            'sign_reminder_days': 3,
            'sign_validity_days': 14,
            'sign_role_ids': [
                (0, 0, {'sequence': 10, 'name': 'Customer', 'signer_type': 'field'}),
                (0, 0, {'sequence': 20, 'name': 'Witness', 'signer_type': 'partner', 'partner_id': cls.witness.id}),
            ],
        })

    def issue(self, partner=None):
        Issue = self.env['print.issue'].with_user(self.sender)
        issue = Issue._create_from_template(self.template, (partner or self.customer).ids)
        issue.action_issue()
        return issue

    def request_for_issue(self, send=True):
        sign_request = self.env['sign.request'].with_user(self.sender)._create_for_issue(self.issue())
        if send:
            sign_request.action_send()
        return sign_request

    def upload_request(self, signers, send=True):
        sign_request = self.env['sign.request'].with_user(self.sender).create({
            'name': 'Uploaded Contract',
            'document_file': BinaryBytes(blank_pdf()),
            'document_filename': 'contract.pdf',
            'signer_ids': [(0, 0, {'sequence': sequence, 'role_name': role, 'partner_id': partner.id})
                           for sequence, role, partner in signers],
        })
        if send:
            sign_request.action_send()
        return sign_request

    @staticmethod
    def signer_of(sign_request, partner):
        return sign_request.signer_ids.filtered(lambda signer: signer.partner_id == partner)

    def sign(self, sign_request, partner):
        self.signer_of(sign_request, partner).sudo()._sign(partner.name, SIGNATURE)
