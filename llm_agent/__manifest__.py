# -*- coding: utf-8 -*-
# Part of Invitech. See LICENSE file for full copyright and licensing details.

{
    'name': 'LLM Agent',
    'version': '5.0',
    'description': '''
        This module provide tools for LLM via API and ChatUI.
    ''',
    'author': 'Intesco Co.,LTD',
    'website': 'https://ivf.com.vn',
    'category': 'Custom',
    'depends': [
        'ims_patient',
        'ims_treatment',
        'ims_test',
        'ims_utility',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/res_partner_data.xml',
        'data/res_users_data.xml',
    ],
    'qweb': [],
    'assets': {},
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'Other proprietary',
}
