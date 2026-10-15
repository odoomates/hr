{
    'name': 'HR Approvals',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Approvals by the manager, the department manager, the coach or HR, and HR requests of the employees',
    'description': 'Adds the approvers of the employee to the approval flows, for the HR documents and for the '
                   'buttons of any app, and lets employees send HR requests approved along a flow. Part of Odoo '
                   'Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_approval', 'om_hr_base'],
    'data': [
        'security/ir.access.csv',
        'data/om_hr_request_data.xml',
        'views/om_approval_flow_views.xml',
        'views/om_hr_request_views.xml',
        'views/menu.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
