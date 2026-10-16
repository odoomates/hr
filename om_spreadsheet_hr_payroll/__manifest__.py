{
    'name': 'Payroll Dashboard',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Payroll dashboard for Odoo 20 Community: gross and net pay by month, department and rule, '
               'top earners',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['spreadsheet_dashboard', 'om_hr_payroll'],
    'data': [
        'data/dashboards.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'om_spreadsheet_hr_payroll/static/tests/tours/**/*',
        ],
    },
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
