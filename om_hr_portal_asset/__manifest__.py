{
    'name': 'HR Portal: Assets',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees see the laptops, phones and tools in their hands on the website portal',
    'description': 'Adds an Assets page to My HR on the website portal: the employees see the assets handed over to '
                   'them, with the serial number, the hand-over and return dates and the status. Installs by itself '
                   'with HR Portal and HR Assets. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_portal', 'om_hr_asset'],
    'data': ['views/portal_templates.xml'],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
