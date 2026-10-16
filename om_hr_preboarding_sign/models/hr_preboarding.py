from odoo import api, fields, models


class HrPreboardingStep(models.Model):
    _inherit = 'hr.preboarding.step'

    kind = fields.Selection(selection_add=[
        ('policies', 'Agree to the Policies'),
        ('signatures', 'Sign the Documents'),
    ], ondelete={'policies': 'cascade', 'signatures': 'cascade'})

    @api.model
    def _auto_kinds(self):
        return super()._auto_kinds() + ['policies', 'signatures']


class HrPreboardingLine(models.Model):
    _inherit = 'hr.preboarding.line'

    def _refresh(self):
        result = super()._refresh()
        for line in self.filtered(lambda line: line.state != 'done'):
            if line.kind == 'policies' and line._policies_done():
                line._mark_done()
            elif line.kind == 'signatures' and line._signatures_done():
                line._mark_done()
        return result

    def _policies_done(self):
        """ :return: whether no policy waits for the answer of the new hire """
        return not self.env['hr.policy.assignment'].sudo().search_count(
            [('employee_id', '=', self.employee_id.id), ('state', '=', 'pending')])

    def _signatures_done(self):
        """ :return: whether the new hire signed what was sent to them, and has nothing left to sign """
        signers = self.env['sign.request.signer'].sudo().search(
            [('partner_id', 'in', (self.employee_id.work_contact_id | self.employee_id.user_id.partner_id).ids),
             ('request_id.state', '!=', 'draft')])
        return any(signer.state == 'signed' for signer in signers) and not any(
            signer.state == 'to_sign' and signer.request_id.state == 'sent' for signer in signers)
