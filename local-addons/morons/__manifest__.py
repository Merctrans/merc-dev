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
    'version': '0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'project', 'account', 'mail', 'auth_totp', 'l10n_generic_coa', 'auth_signup'],

    # always loaded
    'data': [
        'security/moron_security.xml',
        'security/ir.model.access.csv',

        'views/moron_project.xml',
        'views/moron_task.xml',
        'views/moron_contributor.xml',
        'views/moron_contributor_invoice.xml',
        'views/moron_sale_order.xml',
        'views/moron_client_invoice.xml',
        'views/moron_customer.xml',
        'views/moron_service.xml',
        'views/moron_nationality_views.xml',
        'report/moron_sale_report_views.xml',
        # 'report/moron_project_service_report_views.xml',  # pending
        'wizard/account_payment_register_views.xml',
        'wizard/account_invoice_send_views.xml',
        'views/menu_moron.xml',
        'data/mail_template_data.xml',
        'data/languages.xml',
        'data/currencies.xml',
        'data/services.xml',
        'data/tags.xml',
        'data/sequence.xml',
        'data/moron.nationality.csv',
    ],
    "assets": {
        "web.assets_backend": [
            "morons/static/src/webclient/*/*.js",
            "morons/static/src/webclient/*/*.xml",
            "morons/static/src/webclient/*.js",
            "morons/static/src/webclient/*.xml",
            "morons/static/src/components/*/*.js",
            "morons/static/src/components/*/*.xml",
            "morons/static/src/components/*/*.scss",
        ],
    },
    # only loaded in demonstration mode
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
}
