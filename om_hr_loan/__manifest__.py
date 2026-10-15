{
    'name': 'HR Loans',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee loans and salary advances: request, approval flow, monthly installments, repayment',
    'description': 'Employees ask for a loan or a salary advance from My HR. The request is approved along an '
                   'approval flow, the manager then HR by default, within the limits of its loan type: maximum '
                   'amount, number of installments, share of the wage, minimum service. HR pays it out, then it is '
                   'repaid in monthly installments that can be postponed, repaid by hand or settled at once. With '
                   'HR Loans in Payroll, the installments are deducted from the payslips. Part of Odoo Mates HR.',
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
