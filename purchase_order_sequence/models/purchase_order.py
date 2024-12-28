
from odoo import models, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def create(self, vals):
        # Obtener el tipo de orden
        tipo_orden = vals.get('x_studio_tipo_de_orden')

        # Asignar la secuencia según el tipo de orden
        if tipo_orden in ['importacion', 'nacional']:
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order')
        elif tipo_orden == 'indirectos':
            vals['name'] = self.env['ir.sequence'].next_by_code('IN')

        return super(PurchaseOrder, self).create(vals)
