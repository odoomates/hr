{
    'name': 'Payroll Bank Files',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Export the salary transfers of the payslips as the file your bank asks for: CSV, fixed width '
               'or Excel',
    'description': 'Export a bank file from a payslip batch or from payslips: one line per salary transfer, the '
                   'net salary split over the bank accounts of the employee by their salary distribution, in the '
                   'layout of your bank, with the problems shown before you send it. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_file_layout', 'om_hr_payroll'],
    'data': [
        'security/ir.access.csv',
        'data/om_file_layout_data.xml',
        'views/om_hr_payroll_export_views.xml',
        'views/menu.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
