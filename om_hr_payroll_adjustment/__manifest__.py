{
    'name': 'Payroll Adjustments',
    'version': '1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Payroll bonuses, commissions, fines and deductions: once, monthly or until a total, taken by the '
               'payslips',
    'description': 'Additions to and deductions from the pay of an employee besides the contract: a bonus, a '
                   'commission, a fine, a court deduction. Once, for a number of months, or every month until a '
                   'total; a fixed amount or a percentage of the wage or of the gross. Approved when the type asks '
                   'for it, then taken by the payslips month after month, each type on its own payslip line. '
                   'Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_base', 'om_hr_payroll', 'om_hr_approval'],
    'data': [
        'security/ir.access.csv',
        'data/om_hr_payroll_adjustment_data.xml',
        'views/om_hr_payroll_adjustment_type_views.xml',
        'views/om_hr_payroll_adjustment_views.xml',
        'wizard/om_hr_payroll_adjustment_wizard_views.xml',
        'views/menu.xml',
    ],
    'images': ['static/description/banner.gif'],
    'uninstall_hook': 'uninstall_hook',
}
