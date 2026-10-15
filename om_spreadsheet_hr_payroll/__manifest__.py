{
    'name': 'Payroll Dashboard',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Payroll dashboard for Odoo 20 Community: gross and net pay by month, department and rule, '
               'top earners',
    'description': 'The Payroll dashboard in the Human Resources section of the Dashboards app, for the payroll '
                   'officers: gross and net pay, employees paid, average gross and overtime paid over a period, '
                   'gross and net pay by month, gross pay by department and job position, the pay by category, '
                   'the deductions by rule and the top earners, with Period and Department filters. It reads the '
                   'Payroll Analysis of the confirmed payslips, refunds counted negative, and works without '
                   'Accounting. '
                   'Part of Odoo Mates HR.',
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
