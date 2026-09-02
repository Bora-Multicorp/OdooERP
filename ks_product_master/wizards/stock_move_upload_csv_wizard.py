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
                _("No valid rows found. File must contain Serials/Lots, IMEI 1, IMEI 2, Made In")
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
        """Parse XML file content; returns list of dicts with keys lot_name, imei, imei2, made_in."""
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
            made_in = ""
            for child in el:
                tag = child.tag.lower()
                val = (child.text or "").strip()
                if tag in ("lot_name", "serial", "serial_number", "lot", "lot_number"):
                    lot_name = val
                elif tag in ("imei", "imei1", "imei_1"):
                    imei = val
                elif tag in ("imei2", "imei_2"):
                    imei2 = val
                elif tag in ("made_in", "made_in_country", "made_country", "country", "made_in_country_id", "country_of_origin"):
                    made_in = val
            if lot_name:
                rows.append({"lot_name": lot_name, "imei": imei, "imei2": imei2, "made_in": made_in})

        return rows

    def _parse_csv_content(self, file_content):
        """Parse CSV file content; returns list of dicts with keys lot_name, imei, imei2, made_in."""
        try:
            text = file_content.decode("utf-8", errors="replace")
        except Exception as e:
            raise ValidationError(_("Could not read file as text: %s") % e)

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return []

        parsed_lines = [self._parse_csv_line(line) for line in lines]
        first_row = parsed_lines[0]
        has_header = self._is_header_row(first_row)

        if has_header:
            header_map = self._map_header_indices(first_row)
            data_rows = parsed_lines[1:]
        else:
            header_map = None
            data_rows = parsed_lines

        rows = []
        for parts in data_rows:
            if not parts:
                continue
            row_data = self._extract_row_data(parts, header_map)
            if row_data.get("lot_name"):
                rows.append(row_data)
        return rows

    def _parse_xlsx_content(self, file_content):
        """Parse XLSX file content; returns list of dicts with keys lot_name, imei, imei2, made_in."""
        if openpyxl is None:
            raise ValidationError(
                _("Excel (.xlsx) support requires the 'openpyxl' library. Please install it (e.g. pip install openpyxl).")
            )
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True, data_only=True)
        except Exception as e:
            raise ValidationError(_("Could not open Excel file: %s") % e)

        parsed_rows = []
        try:
            ws = wb.active
            if not ws:
                return []
            for row in ws.iter_rows(min_row=1, values_only=True):
                if not row:
                    continue
                row_str_vals = [self._cell_to_str(c) for c in row]
                if any(row_str_vals):
                    parsed_rows.append(row_str_vals)
        finally:
            wb.close()

        if not parsed_rows:
            return []

        first_row = parsed_rows[0]
        has_header = self._is_header_row(first_row)

        if has_header:
            header_map = self._map_header_indices(first_row)
            data_rows = parsed_rows[1:]
        else:
            header_map = None
            data_rows = parsed_rows

        rows = []
        for parts in data_rows:
            if not parts:
                continue
            row_data = self._extract_row_data(parts, header_map)
            if row_data.get("lot_name"):
                rows.append(row_data)
        return rows

    def _is_header_row(self, row):
        if not row:
            return False
        row_str = " ".join(str(c or "").lower() for c in row)
        return any(k in row_str for k in ("serial", "lot", "imei", "made", "country", "origin"))

    def _map_header_indices(self, headers):
        lot_idx = -1
        imei1_idx = -1
        imei2_idx = -1
        made_in_idx = -1

        for idx, h in enumerate(headers):
            h_clean = str(h or "").strip().lower()
            if not h_clean:
                continue
            if ("serial" in h_clean or "lot" in h_clean) and lot_idx == -1:
                lot_idx = idx
            elif ("imei 2" in h_clean or "imei2" in h_clean or "imei_2" in h_clean) and imei2_idx == -1:
                imei2_idx = idx
            elif ("imei 1" in h_clean or "imei1" in h_clean or "imei_1" in h_clean or h_clean == "imei") and imei1_idx == -1:
                imei1_idx = idx
            elif ("made" in h_clean or "country" in h_clean or "origin" in h_clean) and made_in_idx == -1:
                made_in_idx = idx

        if lot_idx == -1 and len(headers) > 0:
            lot_idx = 0

        return {
            "lot_idx": lot_idx,
            "imei1_idx": imei1_idx,
            "imei2_idx": imei2_idx,
            "made_in_idx": made_in_idx,
        }

    def _extract_row_data(self, parts, header_map=None):
        def get_val(idx):
            return str(parts[idx]).strip() if (idx != -1 and idx < len(parts) and parts[idx] is not None) else ""

        if header_map:
            lot_name = get_val(header_map["lot_idx"])
            imei = get_val(header_map["imei1_idx"])
            imei2 = get_val(header_map["imei2_idx"])
            made_in = get_val(header_map["made_in_idx"])
        else:
            lot_name = get_val(0)
            imei = ""
            imei2 = ""
            made_in = ""
            if len(parts) >= 4:
                imei = get_val(1)
                imei2 = get_val(2)
                made_in = get_val(3)
            elif len(parts) == 3:
                p1 = get_val(1)
                p2 = get_val(2)
                if p1.isdigit() and p2.isdigit():
                    imei = p1
                    imei2 = p2
                elif p1.isdigit():
                    imei = p1
                    made_in = p2
                else:
                    made_in = p1
            elif len(parts) == 2:
                p1 = get_val(1)
                if p1.isdigit():
                    imei = p1
                else:
                    made_in = p1

        return {
            "lot_name": lot_name,
            "imei": imei,
            "imei2": imei2,
            "made_in": made_in,
        }

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
