{
    'name': 'HR Lateness Payroll',
    'version': '1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'The lateness penalties of a month taken off the payslips, as payroll adjustments',
    'description': 'Turns the lateness penalties of a month into one Lateness payroll adjustment per employee, a '
                   'deduction taken by the payslip of the month: a fixed amount, a percentage of the daily wage or '
                   'the minutes at the hourly wage, within the monthly cap of the lateness policy. Computed from '
                   'Payroll > Adjustments > Lateness Penalties, or on the 1st of each month for the month before. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_payroll', 'om_hr_lateness', 'om_hr_payroll_adjustment'],
    'data': [
        'security/ir.access.csv',
        'data/om_hr_lateness_payroll_data.xml',
        'views/om_hr_lateness_payroll_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
