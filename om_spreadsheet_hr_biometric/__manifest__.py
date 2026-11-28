{
    'name': 'Biometric Attendance Machine - Dashboard',
    'version': '20.0.1.0.2',
    'category': 'Human Resources',
    'summary': 'Biometric attendance dashboard for Odoo 20 Community: punches by day and device, unknown users, '
               'errors, attendances to review, devices',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['spreadsheet_dashboard', 'om_hr_biometric'],
    'data': [
        'data/dashboards.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'om_spreadsheet_hr_biometric/static/tests/tours/**/*',
        ],
    },
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
