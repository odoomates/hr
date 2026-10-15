{
    'name': 'HR Portal: Certificates',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees ask for salary, employment or experience certificates and download them on the website '
               'portal',
    'description': 'Adds a Certificates page to My HR on the website portal: the employees ask for a certificate, '
                   'follow the request and download the PDF once it is issued. Installs by itself with HR Portal and '
                   'HR Certificates. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_portal', 'om_hr_certificate'],
    'data': ['views/portal_templates.xml'],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
