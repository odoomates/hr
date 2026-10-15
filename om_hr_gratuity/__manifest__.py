{
    'name': 'HR Gratuity',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'End of service gratuity: days of pay per year of service, by band, reduced by reason of leaving',
    'description': 'Computes the end of service gratuity of an exit from a scheme the company describes: the days '
                   'of pay a year of service earns in each band of years, the part kept by reason of leaving and '
                   'years of service, a minimum service and a cap. Part of Odoo Mates HR.',
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
    'images': ['static/description/banner.gif'],
}
