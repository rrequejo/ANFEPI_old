
{
    'name': 'Purchase Order Sequence by Type',
    'version': '1.1',
    'author': 'ANFEPI: Roberto Requejo Jiménez',
    'website': 'https://www.anfepi.com',
    'category': 'Purchases',
    'summary': 'Assigns different sequences to purchase orders based on their type and configures user groups.',
    'depends': ['purchase'],
    'data': [
        'data/groups_and_rules.xml',  # Archivo de datos para grupos y reglas
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
