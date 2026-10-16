{
    'name': 'HR Gratuity',
    'version': '20.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'End of service gratuity: days of pay per year of service, by band, reduced by reason of leaving',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['om_hr_approval', 'om_hr_exit'],
    'data': [
        'security/ir.access.csv',
        'views/om_hr_gratuity_scheme_views.xml',
        'views/om_hr_exit_views.xml',
    ],
    'demo': ['demo/om_hr_gratuity_demo.xml'],
    'images': ['static/description/banner.gif'],
}
