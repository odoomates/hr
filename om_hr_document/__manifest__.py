{
    'name': 'HR Documents',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee documents: passports, visas, work permits and IDs, with reminders before they expire',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_document', 'om_hr_base'],
    'data': [
        'security/ir.access.csv',
        'data/om_document_type_data.xml',
        'views/hr_employee_views.xml',
        'views/om_document_views.xml',
        'views/menu.xml',
    ],
    'demo': ['demo/om_hr_document_demo.xml'],
    'assets': {
        'web.assets_tests': [
            'om_hr_document/static/tests/tours/**/*',
        ],
    },
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
