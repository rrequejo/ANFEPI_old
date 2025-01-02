from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import re

class ImportAccountMoveTxt(models.Model):
    _name = 'import.account.move.txt'
    _description = 'Importación de Póliza de Nómina desde TXT'

    name = fields.Char(default='Importar Póliza de Nómina')
    file_data = fields.Binary(string='Archivo TXT', required=True)
    file_name = fields.Char(string='Nombre del Archivo')
    journal_id = fields.Many2one(
        'account.journal', 
        string='Diario Contable', 
        required=True,
        domain="[('type', '=', 'general')]",
        default=lambda self: self.env['account.journal'].search([('name', 'ilike', 'Nómina')], limit=1)
    )

    @api.model
    def _parse_txt(self, file_content):
        """Parsear contenido del archivo TXT y estructurar datos."""
        lines = file_content.decode('utf-8').splitlines()
        header_data = {}
        move_lines = []

        for line in lines:
            if line.startswith('P'):
                # Procesar encabezado de la póliza
                header_data['date'] = line[1:9].strip()  # Fecha AAAAMMDD
                header_data['reference'] = line[26:80].strip()  # Referencia de nómina
            elif line.startswith('M1'):
                # Procesar movimientos contables
                account_code = line[3:10].strip()
                label = line[10:60].strip()
                debit_credit_flag = line[60:61].strip()
                amount = line[61:80].strip()

                # Convertir código de cuenta contable
                account_code = f"{account_code[:3]}.{account_code[3:5]}.{account_code[5:]}"
                
                move_lines.append({
                    'account_code': account_code,
                    'label': label,
                    'debit': float(amount) if debit_credit_flag == '0' else 0.0,
                    'credit': float(amount) if debit_credit_flag == '1' else 0.0
                })

        return header_data, move_lines

    def import_txt(self):
        """Importar archivo TXT y crear asiento contable."""
        if not self.file_data:
            raise UserError('Debe cargar un archivo TXT para continuar.')

        # Leer y procesar archivo
        file_content = base64.b64decode(self.file_data)
        header_data, move_lines = self._parse_txt(file_content)

        # Validar cuentas contables
        accounts = self.env['account.account'].search([])
        existing_accounts = {acc.code: acc for acc in accounts}

        for line in move_lines:
            if line['account_code'] not in existing_accounts:
                raise UserError(f"La cuenta contable {line['account_code']} no existe. Por favor, créela antes de continuar.")

        # Crear asiento contable
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': header_data['date'],
            'ref': header_data['reference'],
            'line_ids': [(0, 0, {
                'account_id': existing_accounts[line['account_code']].id,
                'name': line['label'],
                'debit': line['debit'],
                'credit': line['credit'],
            }) for line in move_lines]
        }

        move = self.env['account.move'].create(move_vals)

        # Adjuntar archivo
        attachment = self.env['ir.attachment'].create({
            'name': self.file_name,
            'type': 'binary',
            'datas': self.file_data,
            'res_model': 'account.move',
            'res_id': move.id
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Asiento Contable',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
        }

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    type = fields.Selection(selection_add=[('general', 'General')])
