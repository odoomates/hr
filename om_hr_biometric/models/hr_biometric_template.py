from odoo import api, fields, models

FINGERS = [
    (0, 'Left Little Finger'), (1, 'Left Ring Finger'), (2, 'Left Middle Finger'), (3, 'Left Index Finger'),
    (4, 'Left Thumb'), (5, 'Right Thumb'), (6, 'Right Index Finger'), (7, 'Right Middle Finger'),
    (8, 'Right Ring Finger'), (9, 'Right Little Finger'),
]


class HrBiometricTemplate(models.Model):
    """ A fingerprint or face template of a device user, kept only when the company chooses to (biometric data):
    to copy the user to other devices. Attendance managers only. """
    _name = 'hr.biometric.template'
    _description = 'Biometric Template'
    _order = 'device_user_id, kind, index'

    device_user_id = fields.Many2one('hr.biometric.device.user', required=True, ondelete='cascade', index=True)
    device_id = fields.Many2one(related='device_user_id.device_id', store=True)
    company_id = fields.Many2one(related='device_user_id.company_id', store=True, index=True)
    employee_id = fields.Many2one(related='device_user_id.employee_id', store=True, index=True)
    kind = fields.Selection([('finger', 'Fingerprint'), ('face', 'Face')], required=True)
    index = fields.Integer(help='The finger, from 0 (left little finger) to 9 (right little finger).')
    finger = fields.Char(compute='_compute_finger')
    valid = fields.Boolean(default=True)
    data = fields.Text(required=True, help='The template, in base64.')

    _template_uniq = models.Constraint('UNIQUE(device_user_id, kind, index)', 'A template is kept once per finger.')

    @api.depends('kind', 'index')
    def _compute_finger(self):
        names = dict(FINGERS)
        for template in self:
            template.finger = names.get(template.index, '') if template.kind == 'finger' else ''

    @api.model
    def _store(self, device_user, templates):
        """ Keep `templates` (dicts kind, index, valid, data) of `device_user`, replacing those of the same finger. """
        existing = {(t.kind, t.index): t for t in device_user.sudo().template_ids}
        for template in templates:
            if not template.get('data'):
                continue
            vals = {'valid': template.get('valid', True), 'data': template['data']}
            record = existing.get((template['kind'], template['index']))
            if record:
                record.write(vals)
            else:
                self.create(dict(vals, device_user_id=device_user.id, kind=template['kind'],
                                 index=template['index']))
