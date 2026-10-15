{
    'name': 'HR Portal: Time Off',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees see their time off balances, ask for time off and withdraw requests on the website portal',
    'description': 'Adds a Time Off page to My HR on the website portal: the employees see what they have left of '
                   'their allocations, ask for time off and withdraw a request not approved yet. Installs by itself '
                   'with HR Portal and Time Off. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_portal', 'hr_holidays'],
    'data': ['views/portal_templates.xml'],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
