from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestGallery(TransactionCase):
    """ The HR menu of the approval flows offers the HR templates, for the HR documents. """

    def test_manager_then_hr(self):
        manager = new_test_user(self.env, 'om_hr_gallery', groups='base.group_user,om_approval.group_approval_manager')
        Rule = self.env['approval.rule'].with_user(manager)
        templates = {t['key']: t for t in Rule.gallery_load(prefix='hr.')['templates']}
        self.assertIn('hr.request', [m['model'] for m in templates['hr_manager_hr']['models']])
        self.assertNotIn('amount', templates, 'no HR document is confirmed by a button with an amount')
        flow = Rule.browse(Rule.gallery_create('hr_manager_hr', 'hr.request')).with_context(active_test=False)
        self.assertFalse(flow.active)
        self.assertFalse(flow.button_id, 'the document is approved by its own Submit')
        self.assertEqual(flow.step_ids.mapped('approver_type'), ['manager', 'group'])
        self.assertEqual(flow.step_ids[1].group_id, self.env.ref('hr.group_hr_manager'))
        data = Rule.designer_load(flow.id)
        self.assertTrue(data['is_document'])
        self.assertIn('manager', [key for key, _label in data['approver_types']])
        self.assertIn('Manager of the Employee', str(data['preview']['summary']))
