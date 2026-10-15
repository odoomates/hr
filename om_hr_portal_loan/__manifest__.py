{
    'name': 'HR Portal: Loans',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees ask for loans and salary advances and follow their repayment on the website portal',
    'description': 'Adds a Loans page to My HR on the website portal: the employees ask for a loan or a salary '
                   'advance, which goes for approval, and follow the amount still due and each installment. Installs '
                   'by itself with HR Portal and HR Loans. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_portal', 'om_hr_loan'],
    'data': ['views/portal_templates.xml'],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
