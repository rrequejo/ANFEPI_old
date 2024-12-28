from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    tipo_de_orden = fields.Selection([
        ('importacion', 'Importación'),
        ('nacional', 'Nacional'),
        ('indirectos', 'Indirectos'),
    ], string="Tipo de Orden", required=True)
