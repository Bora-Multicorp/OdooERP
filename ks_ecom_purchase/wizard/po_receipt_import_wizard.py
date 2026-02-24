# -*- coding: utf-8 -*-
import base64
import re
from collections import defaultdict
from io import BytesIO

from odoo import _, fields, models
from odoo.exceptions import UserError

try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None


class KsPoReceiptImportWizard(models.TransientModel):
    _name = "ks.po.receipt.import.wizard"
    _description = "Purchase Order Receipt Import Wizard (E-com)"

    file_data = fields.Binary(string="XLSX File", required=True)
    file_name = fields.Char(string="File Name", required=True)

    _ORDER_ID_ALIASES = {"orderid", "order_id", "orderno", "order_no", "ecomorderid"}
    _PRODUCT_CODE_ALIASES = {"asin", "sku", "productcode", "defaultcode", "internalreference", "barcode"}
    _QTY_DONE_ALIASES = {"orderquantity", "qtydone", "quantitydone", "receivedqty", "qtyreceived", "doneqty", "quantity"}

    @staticmethod
    def _normalize_header(value):
        return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())

    @staticmethod
    def _to_string(value):
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _to_float(value, default=0.0):
        if value in (None, ""):
            return default
        try:
            return float(value)
        except Exception as exc:
            raise UserError(_("Invalid number value: %s") % value) from exc

    def _find_header(self, normalized_headers, aliases):
        for alias in aliases:
            if alias in normalized_headers:
                return alias
        return None

    def _extract_sheet_data(self):
        """Extract data from XLSX file"""
        self.ensure_one()
        if load_workbook is None:
            raise UserError(_("Python package 'openpyxl' is required to import XLSX files."))

        if not self.file_name or not self.file_name.lower().endswith(".xlsx"):
            raise UserError(_("Please upload a valid .xlsx file only."))

        try:
            decoded_file = base64.b64decode(self.file_data)
        except Exception as exc:
            raise UserError(_("Unable to decode the uploaded file. Please upload it again.")) from exc

        try:
            workbook = load_workbook(filename=BytesIO(decoded_file), data_only=True)
            sheet = workbook.active
        except Exception as exc:
            raise UserError(_("Unable to read the XLSX file. Please verify file content.")) from exc

        rows = list(sheet.iter_rows(values_only=True))
        if len(rows) < 2:
            raise UserError(_("The XLSX file does not contain importable rows."))

        headers = [self._to_string(cell) for cell in (rows[0] or [])]
        if not any(headers):
            raise UserError(_("Header row is empty in the uploaded file."))

        normalized_headers = {}
        for idx, header in enumerate(headers):
            normalized = self._normalize_header(header)
            if normalized:
                normalized_headers[normalized] = idx

        order_id_key = self._find_header(normalized_headers, self._ORDER_ID_ALIASES)
        asin_key = self._find_header(normalized_headers, self._PRODUCT_CODE_ALIASES)
        qty_done_key = self._find_header(normalized_headers, self._QTY_DONE_ALIASES)

        if not order_id_key:
            raise UserError(_("Missing required column: Order ID."))
        if not asin_key:
            raise UserError(_("Missing required column: ASIN/Product Code."))
        if not qty_done_key:
            raise UserError(_("Missing required column: Quantity Done/Received."))

        receipt_data = []
        for line_no, row in enumerate(rows[1:], start=2):
            if not row or all(cell in (None, "") for cell in row):
                continue

            def get_cell(key):
                idx = normalized_headers.get(key)
                if idx is None or idx >= len(row):
                    return None
                return row[idx]

            order_id = self._to_string(get_cell(order_id_key))
            asin = self._to_string(get_cell(asin_key))
            qty_done = self._to_float(get_cell(qty_done_key), default=0.0)

            if not order_id:
                raise UserError(_("Order ID is missing at row %s.") % line_no)
            if not asin:
                raise UserError(_("ASIN is missing at row %s.") % line_no)
            if qty_done <= 0:
                raise UserError(_("Quantity Done must be greater than 0 at row %s.") % line_no)

            receipt_data.append({
                "line_no": line_no,
                "order_id": order_id,
                "asin": asin,
                "qty_done": qty_done,
            })

        if not receipt_data:
            raise UserError(_("No valid import lines found in the uploaded file."))

        return receipt_data

    def action_import_receipt_data(self):
        """Import receipt data and update stock picking move lines"""
        self.ensure_one()
        receipt_data = self._extract_sheet_data()

        # Group by order_id for processing
        grouped_data = defaultdict(list)
        for row in receipt_data:
            grouped_data[row["order_id"]].append(row)

        updated_count = 0
        skipped_count = 0
        warnings = []

        for order_id, rows in grouped_data.items():
            # Find Purchase Order by ks_ecom_order_id
            # Only search for orders that have ks_ecom_order_id set (e-com imported orders)
            po = self.env["purchase.order"].search([
                ("ks_ecom_order_id", "=", order_id),
                ("ks_ecom_order_id", "!=", False),  # Ensure ks_ecom_order_id is set
            ], limit=1)

            if not po:
                # Check if order exists but doesn't have ks_ecom_order_id
                po_without_ecom = self.env["purchase.order"].search([
                    ("name", "=", order_id)
                ], limit=1)
                
                if po_without_ecom:
                    warnings.append(_("Order ID '%s' found but it's not an e-com imported order (missing ks_ecom_order_id). Only e-com imported orders can be processed.") % order_id)
                else:
                    warnings.append(_("Order ID '%s' not found in Purchase Orders.") % order_id)
                skipped_count += len(rows)
                continue
            
            # Additional validation: ensure the PO has ks_ecom_order_id set
            if not po.ks_ecom_order_id:
                warnings.append(_("Purchase Order %s does not have ks_ecom_order_id set. Only e-com imported orders can be processed.") % po.name)
                skipped_count += len(rows)
                continue

            # Find related stock pickings (receipts) in assigned or confirmed state
            pickings = po.picking_ids.filtered(
                lambda p: p.picking_type_id.code == 'incoming' and p.state in ('assigned', 'confirmed', 'draft')
            )

            if not pickings:
                warnings.append(_("No receipt found for Order ID '%s' (PO: %s).") % (order_id, po.name))
                skipped_count += len(rows)
                continue

            # Use the first available picking (or most recent)
            picking = pickings.sorted('create_date', reverse=True)[0]

            # Process each row for this order
            for row in rows:
                asin = row["asin"]
                qty_done = row["qty_done"]

                # Find product by ASIN (default_code)
                product = self.env["product.product"].search([
                    ("default_code", "=", asin)
                ], limit=1)

                if not product:
                    warnings.append(_("Product with ASIN '%s' not found (Order ID: %s, Row: %s).") % (
                        asin, order_id, row["line_no"]
                    ))
                    skipped_count += 1
                    continue

                # Find move in picking by product
                move = picking.move_ids.filtered(
                    lambda m: m.product_id.id == product.id and m.state != 'cancel'
                )

                if not move:
                    warnings.append(_("Product '%s' (ASIN: %s) not found in receipt for Order ID '%s' (Row: %s).") % (
                        product.name, asin, order_id, row["line_no"]
                    ))
                    skipped_count += 1
                    continue

                # Use the first move if multiple found
                move = move[0]

                # Find or create move line (stock.move.line) for this move
                move_line = move.move_line_ids.filtered(
                    lambda ml: ml.product_id.id == product.id
                )

                if not move_line:
                    # Create move line if it doesn't exist
                    move_line_vals = {
                        "move_id": move.id,
                        "product_id": product.id,
                        "product_uom_id": product.uom_id.id,
                        "location_id": move.location_id.id,
                        "location_dest_id": move.location_dest_id.id,
                        "quantity": qty_done,  # Use 'quantity' field for stock.move.line
                        "picked": True,
                    }
                    self.env["stock.move.line"].create(move_line_vals)
                    updated_count += 1
                else:
                    # Update existing move line(s) - update all matching lines
                    move_line.write({
                        "quantity": qty_done,
                        "picked": True,
                    })
                    updated_count += 1

        # Prepare result message
        result_message = _("Receipt Import Completed:\n")
        result_message += _("- Updated: %s line(s)\n") % updated_count
        result_message += _("- Skipped: %s line(s)\n") % skipped_count

        if warnings:
            result_message += _("\nWarnings:\n")
            for warning in warnings:
                result_message += "- %s\n" % warning

        if updated_count == 0:
            raise UserError(result_message)

        # Show success message with warnings if any
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Receipt Import"),
                "message": result_message,
                "type": "success" if not warnings else "warning",
                "sticky": bool(warnings),
            },
        }

