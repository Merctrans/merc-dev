# -*- coding: utf-8 -*-
{
    'name': "MORONS",

    'summary': """
        Translation Project Management for MercTrans""",

    'description': """
        Long description of module's purpose
    """,

    'author': ["Joe Tang", "Long Nguyen"],
    'website': "https://merctrans.vn",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Morons',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'project', 'account','mail'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/project.xml',
        'views/user.xml',
        'data/languages.xml',
        'data/currencies.xml',
        'data/email_template.xml',
        'data/company_data.xml',
        'data/services.xml',
        'data/tags.xml',

    ],
    "assets": {
        "web.assets_backend": [
            
            "morons/static/src/components/*/*.js",
            "morons/static/src/components/*/*.xml",
            "morons/static/src/components/*/*.scss",
        ],
        
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': False,
}
