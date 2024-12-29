from odoo import _, api, fields, models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    tipo_de_orden = fields.Selection([
        ('importacion', 'Importación'),
        ('nacional', 'Nacional'),
        ('indirectos', 'Indirectos'),
    ], string='Tipo de Orden', required=True, default='importacion')

@api.model
def create(self, vals):
    if vals.get('tipo_de_orden') == 'indirectos':
        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.indirectos') or _('New')
    return super(PurchaseOrder, self).create(vals)

