{
    'name': 'Time Off and Attendance Dashboard',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Time off and attendance dashboard for Odoo 20 Community: time off, requests to approve, hours '
               'worked, overtime',
    'description': 'The Time Off and Attendance dashboard in the Human Resources section of the Dashboards app, '
                   'for the HR officers: time off taken, requests to approve, hours worked and overtime hours over '
                   'a period and month by month, the time off by type and by department, the hours worked and the '
                   'overtime by department, and the list of the time off requests to approve, with Period and '
                   'Department filters. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['spreadsheet_dashboard', 'hr_holidays', 'hr_attendance'],
    'data': [
        'data/dashboards.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'om_spreadsheet_hr_time/static/tests/tours/**/*',
        ],
    },
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
