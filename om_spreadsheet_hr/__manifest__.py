{
    'name': 'HR Dashboards',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'HR dashboard for Odoo 20 Community: headcount, joiners, leavers, turnover, service, contracts '
               'ending',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['spreadsheet_dashboard', 'hr'],
    'data': [
        'data/dashboards.xml',
    ],
    'assets': {
        'spreadsheet.o_spreadsheet_core': [
            (
                'after',
                'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.js',
                'om_spreadsheet_hr/static/src/**/*.js',
            ),
        ],
        'web.assets_tests': [
            'om_spreadsheet_hr/static/tests/tours/**/*',
        ],
    },
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
