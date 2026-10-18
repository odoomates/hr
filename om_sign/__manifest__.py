{
    'name': 'Sign',
    'version': '20.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Send prints and PDF files for electronic signature: signed in order from an email link, with a '
               'signature certificate',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_print_template', 'portal'],
    # the Enterprise app defining the same models
    'excludes': ['sign'],
    'data': [
        'security/sign_security.xml',
        'security/ir.access.csv',
        'data/sign_data.xml',
        'report/sign_reports.xml',
        'views/sign_templates.xml',
        'views/sign_request_views.xml',
        'views/print_views.xml',
        'views/menu.xml',
    ],
    'demo': ['demo/om_sign_demo.xml'],
    'images': ['static/description/banner.gif'],
    'application': True,
}
