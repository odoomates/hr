{
    'name': 'Approvals',
    'version': '1.0.0',
    'category': 'Productivity',
    'summary': 'Approval flows for any app: a button waits for its approval before it runs, e.g. confirming a '
               'sale order above an amount',
    'description': 'Approval rules on the buttons of any model, approved in steps by given users, the users of a '
                   'group or the user a field of the record names, with an inbox of what waits for your '
                   'approval. Other modules use the same flows to approve their own documents. Part of Odoo '
                   'Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/om_approval_security.xml',
        'security/ir.access.csv',
        'data/om_approval_data.xml',
        'wizard/om_approval_refuse_views.xml',
        'views/om_approval_flow_views.xml',
        'views/om_approval_request_views.xml',
        'views/menu.xml',
    ],
    'images': ['static/description/banner.gif'],
}
