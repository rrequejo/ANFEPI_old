from odoo import models, fields

class AccountMoveImportWizard(models.TransientModel):
    _name = 'account.move.import.wizard'
    _description = 'Asistente de Importación de Pólizas'

    file = fields.Binary(string='Archivo TXT', required=True)
    filename = fields.Char(string='Nombre del archivo')

    def import_policies(self):
        import_model = self.env['account.move.import'].create({
            'name': self.filename or 'Importación',
            'file': self.file,
            'filename': self.filename,
        })
        import_model.import_file()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Asiento Contable',
            'res_model': 'account.move',
            'res_id': import_model.move_id.id,
            'view_mode': 'form',
        }
