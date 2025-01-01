from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
from datetime import datetime

class AccountMoveImport(models.Model):
    _name = 'account.move.import'
    _description = 'Importación de Pólizas'

    name = fields.Char(string='Nombre', required=True)
    file = fields.Binary(string='Archivo TXT', required=True)
    filename = fields.Char(string='Nombre del archivo')
    move_id = fields.Many2one('account.move', string='Asiento Contable')

    def import_file(self):
        # Leer el archivo TXT
        if not self.file:
            raise UserError('Por favor, sube un archivo TXT.')

        # Decodificar el archivo
        content = base64.b64decode(self.file).decode('utf-8')
        lines = content.splitlines()

        # Variables para almacenar los datos
        move_vals = {}
        line_vals = []

        for line in lines:
            if line.startswith('P'):
                # Extraer fecha y referencia
                move_vals['date'] = datetime.strptime(line[2:10], '%Y%m%d').date()
                move_vals['ref'] = line[40:80].strip()
            elif line.startswith('M1'):
                # Extraer cuenta, etiqueta, tipo de movimiento y monto
                account_raw = line[2:9].strip()
                account_code = f"{account_raw[:3]}.{account_raw[3:5]}.{account_raw[5:]}"
                label = line[40:80].strip()
                movement_type = int(line[100:101].strip())
                amount = float(line[101:120].strip())

                # Crear línea contable
                line_vals.append((0, 0, {
                    'account_id': self._get_account(account_code).id,
                    'name': label,
                    'debit': amount if movement_type == 0 else 0.0,
                    'credit': amount if movement_type == 1 else 0.0,
                }))

        # Validar datos de la póliza
        if not move_vals:
            raise UserError('No se encontraron datos de cabecera en el archivo.')

        # Crear el asiento contable
        journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        if not journal:
            raise UserError('No se encontró un diario general en el sistema.')

        move_vals.update({
            'journal_id': journal.id,
            'line_ids': line_vals,
        })

        move = self.env['account.move'].create(move_vals)
        self.write({'move_id': move.id})

        # Adjuntar archivo original
        attachment = self.env['ir.attachment'].create({
            'name': self.filename,
            'datas': self.file,
            'res_model': 'account.move',
            'res_id': move.id,
        })

        return move

    def _get_account(self, account_code):
        # Buscar o crear la cuenta contable según el código
        account = self.env['account.account'].search([('code', '=', account_code)], limit=1)
        if not account:
            raise UserError(f'La cuenta contable {account_code} no existe en el sistema.')
        return account
