{
    'name': 'Sign',
    'version': '1.0.0',
    'category': 'Productivity',
    'summary': 'Send prints and PDF files for electronic signature: signed in order from an email link, with a '
               'signature certificate',
    'description': 'Send an issued print or any PDF to the people who sign it. Each one gets a link by email, signs '
                   'by drawing, typing or uploading a signature, without an account, and in the order set: the '
                   'templates name who signs, e.g. the employee and then the manager. An optional code sent by '
                   'email confirms the signer. Once everyone signed, they all get the signed PDF, closed by a '
                   'certificate page with who signed, when, from where and the fingerprint of the document. Part '
                   'of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_print_template', 'portal'],
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
    'images': ['static/description/banner.gif'],
    'application': True,
}
