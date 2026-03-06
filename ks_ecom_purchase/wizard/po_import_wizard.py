import base64
import re
from collections import defaultdict
from datetime import date, datetime
from io import BytesIO

from odoo import Command, _, fields, models
from odoo.exceptions import UserError

try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None


class KsPoImportWizard(models.TransientModel):
    _name = "ks.po.import.wizard"
    _description = "Purchase Order Import Wizard (E-com)"

    file_data = fields.Binary(string="XLSX File", required=True)
    file_name = fields.Char(string="File Name", required=True)
    purchase_id = fields.Many2one("purchase.order", string="Purchase Order")

    _ORDER_ID_ALIASES = {"orderid", "order_id", "orderno", "order_no", "ecomorderid"}
    _VENDOR_ALIASES = {"vendor", "vendorname", "supplier", "suppliername", "partner", "partnername"}
    _PRODUCT_NAME_ALIASES = {"product", "productname", "item", "itemname", "description"}
    # ASIN is prioritized as product internal reference
    _PRODUCT_CODE_ALIASES = {"asin", "sku", "productcode", "defaultcode", "internalreference", "barcode"}
    _QTY_ALIASES = {"orderquantity", "qty", "quantity", "orderedqty", "productqty"}
    _PRICE_ALIASES = {"price", "unitprice", "priceunit", "cost"}
    _SUBTOTAL_ALIASES = {"ordersubtotal", "order_subtotal", "subtotal", "linesubtotal"}
    _UOM_ALIASES = {"uom", "unit", "unitofmeasure"}
    _DATE_ALIASES = {"dateplanned", "planneddate", "expecteddate", "scheduledate", "date"}
    _CURRENCY_ALIASES = {"currency", "currencycode", "curr"}

    _LINE_LEVEL_ALIASES = (
        _PRODUCT_NAME_ALIASES
        | _PRODUCT_CODE_ALIASES
        | _QTY_ALIASES
        | _PRICE_ALIASES
        | _SUBTOTAL_ALIASES
        | _UOM_ALIASES
        | _DATE_ALIASES
        | _CURRENCY_ALIASES
    )

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
        except Exception as exc:  # pragma: no cover - defensive for malformed files
            raise UserError(_("Invalid number value: %s") % value) from exc

    def _find_header(self, normalized_headers, aliases):
        for alias in aliases:
            if alias in normalized_headers:
                return alias
        return None

    def _extract_sheet_data(self):
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
        vendor_key = self._find_header(normalized_headers, self._VENDOR_ALIASES)
        product_name_key = self._find_header(normalized_headers, self._PRODUCT_NAME_ALIASES)
        product_code_key = self._find_header(normalized_headers, self._PRODUCT_CODE_ALIASES)
        qty_key = self._find_header(normalized_headers, self._QTY_ALIASES)
        price_key = self._find_header(normalized_headers, self._PRICE_ALIASES)
        subtotal_key = self._find_header(normalized_headers, self._SUBTOTAL_ALIASES)
        uom_key = self._find_header(normalized_headers, self._UOM_ALIASES)
        date_key = self._find_header(normalized_headers, self._DATE_ALIASES)
        currency_key = self._find_header(normalized_headers, self._CURRENCY_ALIASES)

        if not order_id_key:
            raise UserError(_("Missing required column: Order ID."))
        # Vendor is hardcoded to FLIPKART, so vendor_key check is removed
        if not (product_name_key or product_code_key):
            raise UserError(_("Missing product column. Add Product Name or ASIN/Product Code column."))
        if not qty_key:
            raise UserError(_("Missing required column: Quantity."))

        grouped_rows = defaultdict(list)
        for line_no, row in enumerate(rows[1:], start=2):
            if not row or all(cell in (None, "") for cell in row):
                continue

            def get_cell(key):
                idx = normalized_headers.get(key)
                if idx is None or idx >= len(row):
                    return None
                return row[idx]

            order_id = self._to_string(get_cell(order_id_key))
            # Vendor is hardcoded to FLIPKART
            vendor_name = "FLIPKART"
            product_name = self._to_string(get_cell(product_name_key)) if product_name_key else ""
            # Prioritize ASIN if available, otherwise use other product code fields
            product_code = self._to_string(get_cell(product_code_key)) if product_code_key else ""
            qty = self._to_float(get_cell(qty_key), default=0.0)
            order_subtotal = self._to_float(get_cell(subtotal_key), default=0.0) if subtotal_key else 0.0
            price_direct = self._to_float(get_cell(price_key), default=0.0) if price_key else 0.0
            # Unit price: Order Subtotal / Order Quantity when Subtotal present, else use Price column
            if order_subtotal and qty:
                price_unit = order_subtotal / qty
            else:
                price_unit = price_direct
            uom_name = self._to_string(get_cell(uom_key)) if uom_key else ""
            currency_name = self._to_string(get_cell(currency_key)) if currency_key else ""

            date_raw = get_cell(date_key) if date_key else None
            date_planned = False
            if isinstance(date_raw, datetime):
                date_planned = fields.Datetime.to_string(date_raw)
            elif isinstance(date_raw, date):
                date_planned = fields.Datetime.to_string(datetime.combine(date_raw, datetime.min.time()))
            elif date_raw not in (None, ""):
                date_planned = fields.Datetime.to_string(fields.Datetime.to_datetime(str(date_raw)))

            if not order_id:
                raise UserError(_("Order ID is missing at row %s.") % line_no)
            # Vendor is always FLIPKART, no validation needed
            if not (product_name or product_code):
                raise UserError(_("Product (ASIN/Product Code or Product Name) is missing at row %s.") % line_no)
            if qty <= 0:
                raise UserError(_("Quantity must be greater than 0 at row %s.") % line_no)

            row_raw = {}
            for idx, header in enumerate(headers):
                if not header:
                    continue
                value = row[idx] if idx < len(row) else None
                row_raw[header] = self._to_string(value)

            grouped_rows[order_id].append(
                {
                    "line_no": line_no,
                    "order_id": order_id,
                    "vendor_name": vendor_name,
                    "product_name": product_name,
                    "product_code": product_code,
                    "qty": qty,
                    "price_unit": price_unit,
                    "uom_name": uom_name,
                    "date_planned": date_planned,
                    "currency_name": currency_name,
                    "raw": row_raw,
                }
            )

        if not grouped_rows:
            raise UserError(_("No valid import lines found in the uploaded file."))

        return grouped_rows

    def _get_or_create_vendor(self, vendor_name="FLIPKART"):
        """Get or create FLIPKART vendor partner."""
        partner = self.env["res.partner"].search([("name", "=ilike", vendor_name)], limit=1)
        if not partner:
            partner = self.env["res.partner"].create(
                {
                    "name": vendor_name,
                    "supplier_rank": 1,
                    "company_type": "company",
                }
            )
        elif partner.supplier_rank < 1:
            partner.supplier_rank = 1
        return partner

    def _get_product_by_asin(self, product_code):
        """
        Get product by ASIN (Internal Reference / default_code) only.
        Does NOT create a product. Returns product or empty recordset if not found.
        """
        if not product_code or not str(product_code).strip():
            return self.env["product.product"]
        return self.env["product.product"].search(
            [("default_code", "=", str(product_code).strip())],
            limit=1,
        )

    def _get_uom(self, line_uom_name, product):
        if line_uom_name:
            uom = self.env["uom.uom"].search([("name", "=ilike", line_uom_name)], limit=1)
            if uom:
                return uom
        return product.uom_po_id or product.uom_id

    def _get_currency(self, currency_name, company):
        """Resolve currency from Excel. Fallback to company currency if not found."""
        if not currency_name:
            return company.currency_id
        currency_name = currency_name.strip().upper()
        currency = self.env["res.currency"].search(
            [("name", "=", currency_name)],
            limit=1,
        )
        if currency:
            return currency
        # Try full_name if the column has a long label (e.g. "US Dollar")
        currency = self.env["res.currency"].search(
            [("full_name", "ilike", currency_name)],
            limit=1,
        )
        if currency:
            return currency
        return company.currency_id

    def _prepare_extra_info_commands(self, sample_row):
        excluded_keys = self._ORDER_ID_ALIASES | self._LINE_LEVEL_ALIASES
        commands = []
        for key, value in sample_row.items():
            normalized_key = self._normalize_header(key)
            if not normalized_key or normalized_key in excluded_keys:
                continue
            if value in (None, ""):
                continue
            commands.append(
                Command.create(
                    {
                        "field_key": key,
                        "field_value": self._to_string(value),
                    }
                )
            )
        return commands

    def _build_toast_notification(self, failed_lines, created_orders, total_lines_created):
        """
        Build payloads for Odoo toasts (simple_notification).
        Returns separate payloads for success and for failed ASINs (red/different box).
        """
        failed_count = len(failed_lines)
        success_payload = None
        failed_payload = None

        # Success message (green box) - only when something was created
        if created_orders:
            success_payload = {
                "title": _("PO Import: Success"),
                "message": _("Created: %(po_count)s Purchase Order(s), %(line_count)s line(s).") % {
                    "po_count": len(created_orders),
                    "line_count": total_lines_created,
                },
                "type": "success",
            }

        # Failed ASINs message (red box) - separate message box for records not created
        if failed_count:
            failed_asin_list = ", ".join(item["asin"] for item in failed_lines[:10])
            if failed_count > 10:
                failed_asin_list += _(" and %s more") % (failed_count - 10)
            failed_payload = {
                "title": _("PO Import: Records not created"),
                "message": _("ASIN(s) not found (no matching product): %s") % failed_asin_list,
                "type": "danger",
            }
        elif not created_orders:
            # No failures and no success = empty file or all skipped
            success_payload = {
                "title": _("PO Import"),
                "message": _("No lines imported. Ensure ASINs match product Internal References."),
                "type": "warning",
            }

        return {"success": success_payload, "failed": failed_payload}

    def action_import_purchase_orders(self):
        self.ensure_one()
        grouped_rows = self._extract_sheet_data()

        ecom_tag = self.env["ks.ecom.tag"].sudo().search([("name", "=", "E-com")], limit=1)
        if not ecom_tag:
            ecom_tag = self.env["ks.ecom.tag"].sudo().create({"name": "E-com"})

        vendor = self._get_or_create_vendor("FLIPKART")
        company = self.env.company

        created_orders = self.env["purchase.order"]
        failed_lines = []  # list of {"asin", "order_id", "line_no"}
        total_lines_created = 0

        for order_id, order_rows in grouped_rows.items():
            valid_rows = []
            for row in order_rows:
                product_code = row.get("product_code") or ""
                if not product_code or not str(product_code).strip():
                    failed_lines.append({
                        "asin": product_code or _("(empty)"),
                        "order_id": order_id,
                        "line_no": row["line_no"],
                    })
                    continue
                product = self._get_product_by_asin(product_code)
                if not product:
                    failed_lines.append({
                        "asin": product_code,
                        "order_id": order_id,
                        "line_no": row["line_no"],
                    })
                    continue
                valid_rows.append((row, product))

            if not valid_rows:
                continue

            sample_currency = order_rows[0].get("currency_name") if order_rows else ""
            currency = self._get_currency(sample_currency, company)
            po_vals = {
                "partner_id": vendor.id,
                "origin": _("E-com Import - %s") % order_id,
                "currency_id": currency.id,
                "ks_ecom_imported": True,
                "ks_ecom_order_id": order_id,
                "ks_ecom_source_file": self.file_name,
                "ks_ecom_tag_ids": [Command.link(ecom_tag.id)],
                "ks_ecom_info_ids": self._prepare_extra_info_commands(order_rows[0]["raw"]),
            }
            purchase_order = self.env["purchase.order"].create(po_vals)

            for row, product in valid_rows:
                uom = self._get_uom(row["uom_name"], product)
                line_name = (
                    row["product_name"]
                    or product.name
                    or product.display_name
                    or row["product_code"]
                    or _("Product")
                )
                self.env["purchase.order.line"].create({
                    "order_id": purchase_order.id,
                    "product_id": product.id,
                    "name": line_name,
                    "product_qty": row["qty"],
                    "product_uom": uom.id,
                    "price_unit": row["price_unit"],
                    "date_planned": row["date_planned"] or fields.Datetime.now(),
                })
                total_lines_created += 1

            purchase_order.button_confirm()
            if purchase_order.picking_ids:
                purchase_order.picking_ids.write({"ks_ecom_po_reciept": True})
            created_orders |= purchase_order

        # Show toasts: red box for records not created, green box for success (separate message boxes)
        toasts = self._build_toast_notification(failed_lines, created_orders, total_lines_created)
        bus = self.env["bus.bus"]
        partner_id = self.env.user.partner_id
        # Red message box: ASINs that did not match (records not created)
        if toasts["failed"]:
            bus._sendone(
                partner_id,
                "simple_notification",
                {
                    "type": toasts["failed"]["type"],
                    "title": toasts["failed"]["title"],
                    "message": toasts["failed"]["message"],
                    "sticky": True,
                },
            )
        # Green message box: successfully created POs/lines
        if toasts["success"]:
            bus._sendone(
                partner_id,
                "simple_notification",
                {
                    "type": toasts["success"]["type"],
                    "title": toasts["success"]["title"],
                    "message": toasts["success"]["message"],
                    "sticky": True,
                },
            )

        if not created_orders:
            return {"type": "ir.actions.act_window_close"}

        if len(created_orders) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Purchase Order"),
                "res_model": "purchase.order",
                "view_mode": "form",
                "res_id": created_orders.id,
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Imported Purchase Orders"),
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("id", "in", created_orders.ids)],
            "target": "current",
        }

