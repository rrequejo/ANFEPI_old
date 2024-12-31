# -*- coding: utf-8 -*-
{
    'name': 'Extensión de Mensajes Adjuntos',
    'summary': "Validaciones de Adjuntos",
    'description': 'Validaciones de Adjuntos',

    'author':'ANFEPI: Roberto Requejo Fernández',

    'version': '1.7',
    'depends': ['mail','web','account'],

    'data': [

    ],
    
    'assets': {
        'web.assets_backend': [
            'ir_attachment_message_extend/static/src/js/*.js',
        ],
    },

    'license': "AGPL-3",

    'installable': True,
    'application': True,

    'images': ['static/description/icon.png'],
}
