{
    'name': 'HR Loans in Payroll',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Deduct the employee loan installments from the payslips, and mark them repaid with the payslip',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_loan', 'om_hr_payroll'],
    'data': [
        'data/hr_salary_rule_data.xml',
        'views/om_hr_loan_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
