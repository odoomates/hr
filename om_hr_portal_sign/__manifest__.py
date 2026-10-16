{
    'name': 'HR Portal: Policies',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Employees read and agree to the company policies, or sign them, on the website portal',
    'description': 'The policies the employee is asked to answer, read on the website portal: agreed with one '
                   'click, or signed from the signing page. Their signature requests are in the Signatures page of '
                   'the portal. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_portal', 'om_hr_sign'],
    'data': ['views/portal_templates.xml'],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
