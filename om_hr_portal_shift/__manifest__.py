{
    'name': 'HR Portal: Shifts',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees see their shifts, claim open shifts, swap shifts and give the days they cannot work on the '
               'portal',
    'description': 'Adds a Shifts page to My HR on the website portal: the employees see their upcoming shifts, claim '
                   'open shifts, ask a colleague for a swap, answer the swaps asked of them and give the days they '
                   'cannot work. Installs by itself with HR Portal and Shifts. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_portal', 'om_hr_shift'],
    'data': ['views/portal_templates.xml'],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
