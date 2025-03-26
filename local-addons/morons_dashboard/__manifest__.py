# -*- coding: utf-8 -*-
{
    'name': "MORONS - Dashboard",

    'summary': """
        MORONS - Dashboard""",

    'description': """
    MORONS - Dashboard
    """,

    'author': ["Dlynx"],
    'website': "https://merctrans.vn",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Morons',
    'version': '0.1.0',

    # any module necessary for this one to work correctly
    'depends': ['morons', 'spreadsheet_dashboard'],

    # always loaded
    'data': [
        "data/dashboards.xml",
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
}
