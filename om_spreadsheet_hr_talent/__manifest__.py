{
    'name': 'Talent and Compliance Dashboard',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'HR dashboard for Odoo 20 Community: appraisals, employee documents to renew, exits, employee '
               'assets',
    'description': 'The Talent and Compliance dashboard in the Human Resources section of the Dashboards app, '
                   'for the HR officers: appraisals to do and done with their ratings and status, the employee '
                   'documents expiring and expired by type with the list to renew, the exits in progress by '
                   'reason, and the assets in the hands of the employees, with Period and Department filters. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['spreadsheet_dashboard', 'om_hr_appraisal', 'om_hr_document', 'om_hr_exit', 'om_hr_asset'],
    'data': [
        'data/dashboards.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'om_spreadsheet_hr_talent/static/tests/tours/**/*',
        ],
    },
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
