
{
    'name': 'import_account_move_txt',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Importación de pólizas de nómina desde archivos TXT',
    'author': 'ANFEPI: Roberto Requejo Jiménez',
    'website': 'https://www.anfepi.com',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/import_account_move_txt_views.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
