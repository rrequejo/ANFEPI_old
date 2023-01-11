# -*- coding: utf-8 -*-
# Copyright (C) 2022 Artem Shurshilov <shurshilov.a@yandex.ru>
{
    "name": "Google drive integration",
    "summary": " Google drive google gdrive google disk\
google access token and credentials integration\
",
    "author": "EURO ODOO, Shurshilov Artem",
    "website": "https://eurodoo.com",
    "category": "Technical Settings",
    "version": "15.0.0.0",
    "license": "OPL-1",
    "price": 19,
    "currency": "EUR",
    "images": [
        "static/description/preview.png",
    ],
    # any module necessary for this one to work correctly
    "depends": ["base"],
    "external_dependencies": {
        "python": ["google_auth_oauthlib"],
    },
    # always loaded
    "data": [
        "views/res_config_settings_views.xml",
    ],
}
