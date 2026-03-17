# -*- coding: utf-8 -*-

import base64
import re
from io import BytesIO

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None


class ActivationStatusWizard(models.TransientModel):
    _name = 'activation.status.wizard'
    _description = 'Update Activation Status using CSV'

    csv_file = fields.Binary(string='Excel File', required=False, help='Upload Excel with columns: IMEI, Activation state (Active/Not active)')
    filename = fields.Char(string='Filename')
    result_message = fields.Html(string='Result', readonly=True)

    def _parse_excel_rows(self):
        """Parse uploaded Excel: first column = IMEI, second = Activation state. Returns list of (imei, is_active)."""
        if not load_workbook:
            raise UserError('Please install openpyxl: pip install openpyxl')
        if not self.csv_file or not self.filename:
            raise ValidationError('Please upload an Excel file.')
        if not self.filename.lower().endswith(('.xlsx', '.xlsm', '.xls')):
            raise ValidationError('Unsupported format. Please upload an Excel file (.xlsx, .xlsm, .xls).')

        file_content = base64.b64decode(self.csv_file)
        wb = load_workbook(filename=BytesIO(file_content), data_only=True)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            raise ValidationError('The Excel file is empty.')

        # Optional header row: if first cell looks like "IMEI" or "IEMI", skip it
        start = 0
        if rows and len(rows[0]) >= 2:
            first_cell = (rows[0][0] or '').strip().upper()
            if first_cell in ('IMEI', 'IEMI', 'IMEI NO', 'IMEI NO.'):
                start = 1

        result = []
        for row in rows[start:]:
            if not row or (row[0] is None and row[1] is None):
                continue
            imei_raw = row[0]
            activation_raw = row[1] if len(row) > 1 else None
            if imei_raw is None:
                continue
            imei = re.sub(r'\s+', '', str(imei_raw).strip())
            if not imei:
                continue
            # Normalize activation: Active / Not active (case insensitive)
            is_active = True
            if activation_raw is not None and str(activation_raw).strip():
                val = str(activation_raw).strip().lower()
                if val in ('not active', 'notactive', 'no', '0', 'false', 'inactive'):
                    is_active = False
                elif val in ('active', 'yes', '1', 'true'):
                    is_active = True
            result.append((imei, is_active))
        return result

    def _find_quants_by_imei(self, imei):
        """Find all stock.quant where the given IMEI matches either imei or imei2."""
        return self.env['stock.quant'].search([
            '|', ('imei', '=', imei), ('imei2', '=', imei)
        ])

    def action_process_file(self):
        self.ensure_one()
        rows = self._parse_excel_rows()
        if not rows:
            raise ValidationError('No valid IMEI rows found in the file. Expected columns: IMEI, Activation state (Active/Not active).')

        # Duplicate IMEI detection (in file)
        imei_seen = {}
        duplicates = []
        for imei, _ in rows:
            if imei in imei_seen:
                duplicates.append(imei)
            imei_seen[imei] = True
        if duplicates:
            unique_dupes = list(dict.fromkeys(duplicates))
            raise ValidationError(
                'Duplicate IMEI(s) in the file (each IMEI should appear only once): %s' % ', '.join(unique_dupes)
            )

        updated = 0
        failed_imeis = []

        for imei, is_active in rows:
            quants = self._find_quants_by_imei(imei)
            if not quants:
                failed_imeis.append(imei)
                continue
            # Update activation_status (and activation_date) on every matching quant (imei or imei2)
            quants.write({
                'activation_status': is_active,
                'activation_date': fields.Date.today() if is_active else False,
            })
            updated += len(quants)

        # Build result message and keep wizard open so user sees it
        failed_list = '<br/>'.join(failed_imeis) if failed_imeis else 'None'
        msg = (
            '<p><strong>Updated:</strong> %s</p>'
            '<p><strong>Failed (IMEI not found):</strong> %s</p>'
            '<p><strong>Failed IMEI list:</strong></p><p>%s</p>'
        ) % (updated, len(failed_imeis), failed_list or '-')
        self.write({'result_message': msg})

        # Reopen the same wizard record so the form stays open and shows the result.
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'activation.status.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }
