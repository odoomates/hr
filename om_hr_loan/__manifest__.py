{
    'name': 'HR Loans',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee loans and salary advances: request, approval flow, monthly installments, repayment',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_base', 'om_hr_approval'],
    'data': [
        'security/ir.access.csv',
        'data/om_hr_loan_data.xml',
        'views/om_hr_loan_type_views.xml',
        'views/om_hr_loan_views.xml',
        'views/menu.xml',
    ],
    'images': ['static/description/banner.gif'],
}
