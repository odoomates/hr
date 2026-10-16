from odoo import _, models
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def action_grant_portal(self):
        """ A portal user for the employee, invited by email: they reach their HR pages on the website without
            being a user of the backend. """
        self.ensure_one()
        if not self.env.user.has_group('hr.group_hr_user'):
            raise UserError(_('Only HR gives the employees their portal access.'))
        if self.user_id:
            raise UserError(_('%(employee)s already has the user %(user)s.', employee=self.name,
                              user=self.user_id.login))
        email = self.work_email or self.private_email
        if not email:
            raise UserError(_('Set the work email of %s first: the invitation is sent there.', self.name))
        Users = self.env['res.users'].sudo()
        user = Users.with_context(active_test=False).search([('login', '=', email)], limit=1)
        if user and not user.share:
            raise UserError(_('%s is already the login of a user of the backend: link that user instead.', email))
        if user and user.employee_ids:
            raise UserError(_('The portal user %(login)s already belongs to %(employee)s.', login=email,
                              employee=user.employee_ids[0].name))
        if not user:
            partner = self.sudo().work_contact_id
            user = Users.with_context(no_reset_password=True).create({
                'name': self.name,
                'login': email,
                'email': email,
                'partner_id': partner.id if partner and not partner.user_ids else False,
                'company_id': self.company_id.id,
                'company_ids': [(6, 0, self.company_id.ids)],
                'group_ids': [(6, 0, [self.env.ref('base.group_portal').id])],
            })
        user.active = True
        self.sudo().user_id = user
        user.action_reset_password()
        self.message_post(body=_('Portal access granted: an invitation was sent to %s.', email))
        return True
