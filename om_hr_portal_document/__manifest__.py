{
    'name': 'HR Portal: Documents',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees see their passports, visas, permits and IDs and send renewed files on the website portal',
    'description': 'Adds a Documents page to My HR on the website portal: the employees see their documents with the '
                   'expiry dates, download the files and send a renewed file, which HR then checks. Installs by '
                   'itself with HR Portal and HR Documents. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_portal', 'om_hr_document'],
    'data': ['views/portal_templates.xml'],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
