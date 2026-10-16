{
    'name': 'HR Portal',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee self-service portal: profile, payslips, time off, loans, certificates, documents and more on '
               'the website',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['portal', 'om_hr_base'],
    'data': [
        'data/portal_entry_data.xml',
        'views/portal_templates.xml',
        'views/hr_employee_views.xml',
    ],
    'images': ['static/description/banner.gif'],
}
