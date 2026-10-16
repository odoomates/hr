{
    'name': 'HR Job Offers',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Job offers approved, signed by the company and the candidate, and turned into the contract',
    'description': 'Make the job offer from the applicant: position, salary, start date, employee type, working '
                   'schedule, probation and other benefits. Once approved along its approval flow, the offer letter '
                   'is signed by the company, then by the candidate from a link sent by email, without an account. '
                   'Accepted, the applicant moves to the hired stage, and Create Employee fills the contract of the '
                   'new employee from the offer. Part of Odoo Mates HR.',
    'author': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'license': 'LGPL-3',
    'depends': ['hr_recruitment', 'om_sign', 'om_approval'],
    'data': [
        'security/offer_security.xml',
        'security/ir.access.csv',
        'data/offer_data.xml',
        'views/offer_views.xml',
    ],
    'images': ['static/description/banner.gif'],
    'auto_install': True,
}
