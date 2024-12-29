from odoo import models, fields, api, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    tipo_de_orden = fields.Selection([
        ('importacion', 'Importación'),
        ('nacional', 'Nacional'),
        ('indirectos', 'Indirectos')
    ], string="Tipo de Orden")

    @api.model
    def create(self, vals):
        if vals.get('tipo_de_orden') == 'indirectos':
            # Añadimos un log para depurar el proceso
            _logger = logging.getLogger(__name__)
            _logger.info("Asignando secuencia para Indirectos...")
            
            # Verificamos que next_by_code esté buscando correctamente el código "IN"
            vals['name'] = self.env['ir.sequence'].next_by_code('IN') or _('New')
            
            _logger.info("Secuencia asignada: %s", vals['name'])
        
        return super(PurchaseOrder, self).create(vals)

