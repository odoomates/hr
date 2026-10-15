{
    'name': 'HR Dashboards',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'HR dashboard for Odoo 20 Community: headcount, joiners, leavers, turnover, service, contracts '
               'ending',
    'description': 'The Workforce dashboard in the Human Resources section of the Dashboards app, for the HR '
                   'officers: headcount, joiners, leavers, turnover and average service over a period and month by '
                   'month, the employees by department, job position, nationality and type, and the contracts '
                   'ending, with Period and Department filters. It adds the OM.HR spreadsheet formulas, usable in '
                   'any spreadsheet, that count the employees under contract on a date, the joiners, the leavers '
                   'and their average service, archived employees included. '
                   'Part of Odoo Mates HR.',
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
