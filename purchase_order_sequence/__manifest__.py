
{
    'name': 'Purchase Order Sequence by Type',
    'version': '1.1',
    'author': 'ANFEPI: Roberto Requejo Jiménez',
    'website': 'https://www.anfepi.com',
    'category': 'Purchases',
    'summary': 'Assigns different sequences to purchase orders based on their type and configures user groups.',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/purchase_order_views.xml',
        'data/ir_sequence_data.xml',
        'data/groups_and_rules.xml',
    ],
    'installable': True,
    'application': False,
}
