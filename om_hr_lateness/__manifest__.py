{
    'name': 'HR Lateness',
    'version': '1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Late arrivals and early departures against the working schedule: grace minutes, penalty matrix, '
               'warnings, excuses',
    'description': 'Records each late arrival and early departure beyond the grace minutes, against the working '
                   'schedule of the employee with time off and public holidays left out, numbers them in the month '
                   'and gives each the penalty of the lateness policy: a warning, a fixed amount, a percentage of '
                   'the daily wage or the minutes at the hourly wage. Managers excuse them. With Payroll '
                   'Adjustments, the penalties of a month are taken off the payslips. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['hr_attendance', 'om_hr_base'],
    'data': [
        'security/ir.access.csv',
        'data/om_hr_lateness_data.xml',
        'views/om_hr_lateness_views.xml',
    ],
    'images': ['static/description/banner.gif'],
}
