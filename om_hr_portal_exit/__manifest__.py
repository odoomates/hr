{
    'name': 'HR Portal: Resignation',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees hand in their resignation and follow their exit and its clearance on the website portal',
    'description': 'Adds a Resignation page to My HR on the website portal: the employees hand in their resignation, '
                   'which goes for approval, and follow their exit, the last working day and the clearance. Installs '
                   'by itself with HR Portal and HR Exit. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_portal', 'om_hr_exit'],
    'data': ['views/portal_templates.xml'],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
