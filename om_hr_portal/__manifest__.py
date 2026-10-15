{
    'name': 'HR Portal',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee self-service portal: profile, payslips, time off, loans, certificates, documents and more on '
               'the website',
    'description': 'The employees reach their HR on the website portal, from a phone or a computer, without being '
                   'users of the backend. HR invites them with Grant Portal Access on the employee form. A My HR page '
                   'shows their profile and the pages of the HR modules installed, each one showing only what belongs '
                   'to the employee logged in. Part of Odoo Mates HR.',
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
