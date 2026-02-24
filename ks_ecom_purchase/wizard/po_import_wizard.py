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
    _UOM_ALIASES = {"uom", "unit", "unitofmeasure"}
    _DATE_ALIASES = {"dateplanned", "planneddate", "expecteddate", "scheduledate", "date"}

    _LINE_LEVEL_ALIASES = (
        _PRODUCT_NAME_ALIASES
        | _PRODUCT_CODE_ALIASES
        | _QTY_ALIASES
        | _PRICE_ALIASES
        | _UOM_ALIASES
        | _DATE_ALIASES
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
        uom_key = self._find_header(normalized_headers, self._UOM_ALIASES)
        date_key = self._find_header(normalized_headers, self._DATE_ALIASES)

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
            price_unit = self._to_float(get_cell(price_key), default=0.0) if price_key else 0.0
            uom_name = self._to_string(get_cell(uom_key)) if uom_key else ""

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

    def _get_or_create_product(self, product_name, product_code):
        """
        Get or create product using ASIN (product_code) as internal reference.
        ASIN is stored in default_code field for product lookup.
        """
        product = self.env["product.product"]
        # Prioritize ASIN/product_code (default_code) for product lookup
        if product_code:
            product = self.env["product.product"].search([("default_code", "=", product_code)], limit=1)
        # Fallback to product name if ASIN not found
        if not product and product_name:
            product = self.env["product.product"].search([("name", "=ilike", product_name)], limit=1)
        # Create product if not found, using ASIN as default_code
        if not product:
            # Ensure product name is never empty
            product_name_final = product_name or product_code or _("Product")
            template_vals = {
                "name": product_name_final,
                "purchase_ok": True,
                "sale_ok": False,
                "type": "consu",  # In Odoo 18, field is 'type', not 'detailed_type'
            }
            # Always set ASIN as default_code (internal reference)
            if product_code:
                template_vals["default_code"] = product_code
            template = self.env["product.template"].create(template_vals)
            product = template.product_variant_id
            # Ensure product has a valid name after creation
            if not product.name or product.name == _("Product"):
                product.name = product_name_final
        return product

    def _get_uom(self, line_uom_name, product):
        if line_uom_name:
            uom = self.env["uom.uom"].search([("name", "=ilike", line_uom_name)], limit=1)
            if uom:
                return uom
        return product.uom_po_id or product.uom_id

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

    def action_import_purchase_orders(self):
        self.ensure_one()
        grouped_rows = self._extract_sheet_data()

        ecom_tag = self.env["ks.ecom.tag"].sudo().search([("name", "=", "E-com")], limit=1)
        if not ecom_tag:
            ecom_tag = self.env["ks.ecom.tag"].sudo().create({"name": "E-com"})

        # Get or create FLIPKART vendor (hardcoded)
        vendor = self._get_or_create_vendor("FLIPKART")
        
        created_orders = self.env["purchase.order"]
        for order_id, order_rows in grouped_rows.items():
            # Vendor is always FLIPKART, no need to check multiple vendors
            po_vals = {
                "partner_id": vendor.id,
                "origin": _("E-com Import - %s") % order_id,
                "ks_ecom_imported": True,
                "ks_ecom_order_id": order_id,
                "ks_ecom_source_file": self.file_name,
                "ks_ecom_tag_ids": [Command.link(ecom_tag.id)],
                "ks_ecom_info_ids": self._prepare_extra_info_commands(order_rows[0]["raw"]),
            }
            purchase_order = self.env["purchase.order"].create(po_vals)

            for row in order_rows:
                product = self._get_or_create_product(row["product_name"], row["product_code"])
                uom = self._get_uom(row["uom_name"], product)
                # Ensure name is never empty - use product name, ASIN, or fallback
                line_name = row["product_name"] or product.name or product.display_name or row["product_code"] or _("Product")

                self.env["purchase.order.line"].create(
                    {
                        "order_id": purchase_order.id,
                        "product_id": product.id,
                        "name": line_name,
                        "product_qty": row["qty"],
                        "product_uom": uom.id,
                        "price_unit": row["price_unit"],
                        "date_planned": row["date_planned"] or fields.Datetime.now(),
                    }
                )

            created_orders |= purchase_order

        if not created_orders:
            raise UserError(_("No purchase order was created from the uploaded file."))

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

