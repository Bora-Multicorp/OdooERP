# -*- coding: utf-8 -*-
import base64
import io
import xml.etree.ElementTree as ET

from odoo import models, fields, _
from odoo.exceptions import UserError, ValidationError

# Optional: required only for .xlsx import
try:
    import openpyxl
except ImportError:
    openpyxl = None


class StockMoveUploadCsvWizard(models.TransientModel):
    _name = "stock.move.upload.csv.wizard"
    _description = "Upload Serials/Lots and IMEI from CSV, Excel or XML"

    move_id = fields.Many2one("stock.move", string="Stock Move", required=True, ondelete="cascade")
    csv_file = fields.Binary(string="File (CSV, Excel or XML)", required=True)
    filename = fields.Char(string="Filename")
    keep_lines = fields.Boolean(string="Keep current lines", default=False)

    SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xml")

    def action_import(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_("No move specified."))
        if not self.csv_file or not self.filename:
            raise ValidationError(_("Please upload a file (CSV, Excel or XML)."))

        fn_lower = self.filename.lower()
        if not any(fn_lower.endswith(ext) for ext in self.SUPPORTED_EXTENSIONS):
            raise ValidationError(
                _("Unsupported file format. Only .csv, .xlsx and .xml files are allowed.")
            )

        try:
            file_content = base64.b64decode(self.csv_file)
        except Exception as e:
            raise ValidationError(_("Could not decode file: %s") % e)

        if fn_lower.endswith(".xlsx"):
            rows = self._parse_xlsx_content(file_content)
        elif fn_lower.endswith(".xml"):
            rows = self._parse_xml_content(file_content)
        else:
            rows = self._parse_csv_content(file_content)

        if not rows:
            raise ValidationError(
                _("No valid rows found. File must contain Serials/Lots, IMEI 1, IMEI 2")
            )

        self.move_id.action_apply_csv_serial_lines(rows, keep_lines=self.keep_lines)
        return {"type": "ir.actions.act_window_close"}

    def action_download_sample_xlsx(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_("No stock move specified."))
        return self.move_id.action_download_sample_xlsx()

    def action_download_sample_xml(self):
        return self.action_download_sample_xlsx()

    def _parse_xml_content(self, file_content):
        """Parse XML file content; returns list of dicts with keys lot_name, imei, imei2."""
        try:
            root = ET.fromstring(file_content)
        except Exception as e:
            raise ValidationError(_("Could not parse XML file: %s") % e)

        rows = []
        lines = root.findall(".//line") or root.findall(".//row") or root.findall(".//item")
        if not lines:
            lines = list(root)

        for el in lines:
            lot_name = ""
            imei = ""
            imei2 = ""
            for child in el:
                tag = child.tag.lower()
                val = (child.text or "").strip()
                if tag in ("lot_name", "serial", "serial_number", "lot", "lot_number"):
                    lot_name = val
                elif tag in ("imei", "imei1", "imei_1"):
                    imei = val
                elif tag in ("imei2", "imei_2"):
                    imei2 = val
            if lot_name:
                rows.append({"lot_name": lot_name, "imei": imei, "imei2": imei2})

        return rows

    def _parse_csv_content(self, file_content):
        """Parse CSV file content; returns list of dicts with keys lot_name, imei, imei2."""
        try:
            text = file_content.decode("utf-8", errors="replace")
        except Exception as e:
            raise ValidationError(_("Could not read file as text: %s") % e)

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
        return rows

    def _parse_xlsx_content(self, file_content):
        """Parse XLSX file content; returns list of dicts with keys lot_name, imei, imei2."""
        if openpyxl is None:
            raise ValidationError(
                _("Excel (.xlsx) support requires the 'openpyxl' library. Please install it (e.g. pip install openpyxl).")
            )
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True, data_only=True)
        except Exception as e:
            raise ValidationError(_("Could not open Excel file: %s") % e)

        rows = []
        try:
            ws = wb.active
            if not ws:
                return rows
            for row in ws.iter_rows(min_row=1, values_only=True):
                if not row:
                    continue
                lot_name = self._cell_to_str(row[0] if len(row) > 0 else None)
                imei = self._cell_to_str(row[1] if len(row) > 1 else None)
                imei2 = self._cell_to_str(row[2] if len(row) > 2 else None)
                if not lot_name:
                    continue
                if not rows and self._is_header_row(lot_name, imei, imei2):
                    continue
                rows.append({"lot_name": lot_name, "imei": imei, "imei2": imei2})
        finally:
            wb.close()
        return rows

    def _cell_to_str(self, value):
        """Convert a cell value (possibly number/date) to stripped string for consistent mapping."""
        if value is None:
            return ""
        if isinstance(value, bool):
            return "True" if value else "False"
        if isinstance(value, (int, float)):
            return str(int(value) if value == int(value) else value).strip()
        return str(value).strip()

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
