# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError

class Certificate(models.Model):
    _inherit = 'l10n_mx_edi.certificate'

    # Field to know if it is a FIEL certificate or a Certificado de Sello Digital certificate
    l10n_mx_fiel = fields.Boolean("FIEL")

    # Field to store certificate file name
    content_name = fields.Char("Nombre del Archivo")

    # Field to store private key file name
    key_name = fields.Char("Nombre del Archivo")