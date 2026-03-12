# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockMoveUploadCsvWizard(models.TransientModel):
    _name = "stock.move.upload.csv.wizard"
    _description = "Upload Serials/Lots and IMEI from CSV"

    move_id = fields.Many2one("stock.move", string="Stock Move", required=True, ondelete="cascade")
    csv_file = fields.Binary(string="CSV File", required=True)
    filename = fields.Char(string="Filename")
    keep_lines = fields.Boolean(string="Keep current lines", default=False)

    def action_import(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_("No move specified."))
        if not self.csv_file or not self.filename:
            raise ValidationError(_("Please upload a CSV file."))
        if not self.filename.lower().endswith(".csv"):
            raise ValidationError(_("Please upload a CSV file."))

        try:
            file_content = base64.b64decode(self.csv_file)
            text = file_content.decode("utf-8", errors="replace")
        except Exception as e:
            raise ValidationError(_("Could not read file: %s") % e)

        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = self._parse_csv_line(line)
            if len(parts) < 1:
                continue
            lot_name = (parts[0] or "").strip()
            imei = (parts[1] if len(parts) > 1 else "").strip()
            imei2 = (parts[2] if len(parts) > 2 else "").strip()
            if not lot_name:
                continue
            if not rows and self._is_header_row(lot_name, imei, imei2):
                continue
            rows.append({"lot_name": lot_name, "imei": imei, "imei2": imei2})

        if not rows:
            raise ValidationError(
                _("No valid rows found. CSV must have 3 columns: Serials/Lots, IMEI 1, IMEI 2")
            )

        self.move_id.action_apply_csv_serial_lines(rows, keep_lines=self.keep_lines)
        return {"type": "ir.actions.act_window_close"}

    def _parse_csv_line(self, line):
        result = []
        current = []
        in_quotes = False
        for c in line:
            if c == '"':
                in_quotes = not in_quotes
            elif not in_quotes and c in (",", "\t"):
                result.append("".join(current).strip())
                current = []
            else:
                current.append(c)
        result.append("".join(current).strip())
        return result

    def _is_header_row(self, col0, col1, col2):
        a, b, c = (col0 or "").lower(), (col1 or "").lower(), (col2 or "").lower()
        return (
            (("serial" in a or "lot" in a) and "imei" in b and "imei" in c)
        )

