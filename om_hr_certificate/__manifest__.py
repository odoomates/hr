{
    'name': 'HR Certificates',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Salary, employment and experience certificates and NOC: requested by the employees, approved, '
               'printed on the letterhead',
    'description': 'Employees ask for a certificate, e.g. a salary certificate for a bank, approved along an '
                   'approval flow, then printed from its template and downloaded. HR also prints them from the '
                   'Print menu of the employee. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_base', 'om_print_template', 'om_hr_approval'],
    'data': [
        'security/ir.access.csv',
        'data/om_hr_certificate_data.xml',
        'views/om_hr_certificate_views.xml',
        'views/menu.xml',
    ],
    'images': ['static/description/banner.gif'],
}
