# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_mx_edi_fiel_ids = fields.Many2many(
        comodel_name='l10n_mx_edi.certificate',
        relation='l10n_mx_edi_fiel_company_rel',
        column1='company_id', column2='fiel_id',
        string='FIEL (MX)',
        domain=[('l10n_mx_fiel', '=', True),])
    
    l10n_mx_edi_certificate_ids = fields.One2many(
        comodel_name='l10n_mx_edi.certificate',
        inverse_name='company_id',
        string='Certificates (MX)',
        domain=[('l10n_mx_fiel', '=', False)],)
        
        

    
