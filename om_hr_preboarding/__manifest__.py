{
    'name': 'HR Pre-boarding',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'New hires get ready before their first day: their details for HR, reviewed, and what to know',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_portal'],
    'data': [
        'security/ir.access.csv',
        'data/preboarding_data.xml',
        'views/portal_templates.xml',
        'views/hr_preboarding_views.xml',
    ],
    'demo': ['demo/om_hr_preboarding_demo.xml'],
    'images': ['static/description/banner.gif'],
}
