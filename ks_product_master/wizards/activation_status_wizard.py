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

        # Optional header row: skip if first cell looks like an IMEI column header
        _HEADER_VARIANTS = {'IMEI', 'IEMI', 'IMIE', 'IMEI NO', 'IMEI NO.', 'IMEI NUMBER', 'SERIAL', 'SERIAL NO', 'S/N'}
        start = 0
        if rows and rows[0] and rows[0][0] is not None:
            first_cell = str(rows[0][0]).strip().upper()
            if first_cell in _HEADER_VARIANTS or not any(c.isdigit() for c in first_cell):
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

    def _notify(self, title, message, notif_type='success', sticky=False):
        """Return a display_notification action that closes the dialog after showing the toast."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notif_type,   # 'success', 'warning', 'danger', 'info'
                'sticky': sticky,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_process_file(self):
        self.ensure_one()
        try:
            rows = self._parse_excel_rows()
        except (ValidationError, UserError) as e:
            return self._notify(
                title='Import Failed',
                message=str(e.args[0] if e.args else e),
                notif_type='danger',
                sticky=True,
            )
        except Exception as e:
            return self._notify(
                title='Import Failed',
                message='An unexpected error occurred: %s' % str(e),
                notif_type='danger',
                sticky=True,
            )

        if not rows:
            return self._notify(
                title='Import Failed',
                message='No valid IMEI rows found. Expected columns: IMEI, Activation state (Active/Not active).',
                notif_type='danger',
                sticky=True,
            )

        # Reject the entire file if any row tries to set activation to False
        false_rows = [imei for imei, is_active in rows if not is_active]
        if false_rows:
            return self._notify(
                title='Import Failed',
                message=(
                    'Error: Activation Status can only be updated to True. '
                    'Manual deactivation via import is not permitted.\n'
                    'Affected IMEI(s): %s'
                ) % ', '.join(false_rows),
                notif_type='danger',
                sticky=True,
            )

        # Duplicate IMEI detection (in file)
        imei_seen = {}
        duplicates = []
        for imei, _ in rows:
            if imei in imei_seen:
                duplicates.append(imei)
            imei_seen[imei] = True
        if duplicates:
            unique_dupes = list(dict.fromkeys(duplicates))
            return self._notify(
                title='Import Failed',
                message='Duplicate IMEI(s) in the file (each IMEI must appear only once): %s' % ', '.join(unique_dupes),
                notif_type='danger',
                sticky=True,
            )

        updated = 0
        already_uptodate = 0
        failed_imeis = []

        for imei, is_active in rows:
            quants = self._find_quants_by_imei(imei)
            if not quants:
                failed_imeis.append(imei)
                continue
            # Check if already at the desired state (re-import scenario)
            needs_update = quants.filtered(lambda q: q.activation_status != is_active)
            if needs_update:
                needs_update.write({
                    'activation_status': is_active,
                    'activation_date': fields.Date.today() if is_active else False,
                })
                updated += 1        # count IMEIs updated, not quant records
            else:
                already_uptodate += 1  # count IMEIs already at correct state

        if not failed_imeis:
            # Full success — all IMEIs were found (some may have been already up to date)
            if updated == 0 and already_uptodate > 0:
                msg = 'All %d record(s) were already up to date. No changes made.' % already_uptodate
            elif already_uptodate > 0:
                msg = 'Updated: %d record(s). Already up to date: %d record(s).' % (updated, already_uptodate)
            else:
                msg = 'Updated: %d record(s).' % updated
            return self._notify(
                title='Import: Success',
                message=msg,
                notif_type='success',
            )
        else:
            return self._notify(
                title='Import: Completed with Warnings',
                message='Updated: %d | Already up to date: %d | Not found in system: %d\nMissing IMEIs: %s' % (
                    updated, already_uptodate, len(failed_imeis), ', '.join(failed_imeis)
                ),
                notif_type='warning',
                sticky=True,
            )
