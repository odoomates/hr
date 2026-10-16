{
    'name': 'Payroll Adjustments',
    'version': '20.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Payroll bonuses, commissions, fines and deductions: once, monthly or until a total, taken by the '
               'payslips',
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
    'demo': ['demo/om_hr_payroll_adjustment_demo.xml'],
    'images': ['static/description/banner.gif'],
    'uninstall_hook': 'uninstall_hook',
}
