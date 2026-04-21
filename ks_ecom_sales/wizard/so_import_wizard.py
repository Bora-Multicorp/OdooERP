import base64
import logging
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

_logger = logging.getLogger(__name__)


class KsSoImportWizard(models.TransientModel):
    _name = "ks.so.import.wizard"
    _description = "Sale Order Import Wizard (E-com)"

    file_data = fields.Binary(string="XLSX File", required=True)
    file_name = fields.Char(string="File Name", required=True)

    # ─── Header alias sets ───────────────────────────────────────────────────
    _ORDER_ID_ALIASES = {"orderid", "order_id", "orderno", "order_no", "ecomorderid"}
    _ORDER_DATE_ALIASES = {"orderdate", "order_date", "date", "saledate"}
    _CUSTOMER_ALIASES = {
        "customer", "customername", "buyer", "buyername", "client", "clientname",
        "partner", "partnername",
    }
    _COMPANY_ALIASES = {"company", "companyname", "branch", "companybranch"}
    _WAREHOUSE_ALIASES = {"warehouse", "warehousename", "wh", "shipfrom", "ship_from"}
    _ASIN_ALIASES = {"asin", "sku", "productcode", "defaultcode", "internalreference"}
    _QTY_ALIASES = {"quantity", "qty", "orderedqty", "productqty"}
    _RATE_ALIASES = {"rate", "unitprice", "price", "priceunit"}
    _TOTAL_ALIASES = {"totalamount", "total_amount", "subtotal", "linesubtotal", "amount"}
    _DISCOUNT_ALIASES = {"discount", "disc", "discountpercent", "discount_percent"}
    _TAX_ALIASES = {"tax", "taxname", "taxrate", "gst", "vat"}
    _TITLE_ALIASES = {"title", "product", "productname", "item", "description", "itemname"}
    _INVOICE_AMOUNT_ALIASES = {"invoiceamount", "invoice_amount", "invoicevalue"}
    _INVOICE_ID_ALIASES = {"invoiceid", "invoice_id", "invoiceno", "invoice_no"}
    _INVOICE_DATE_ALIASES = {"invoicedate", "invoice_date"}
    _SHIPMENT_ID_ALIASES = {"shipmentid", "shipment_id", "shipmentno", "awb"}
    _SHIPMENT_DATE_ALIASES = {"shipmentdate", "shipment_date", "shippingdate"}
    _SHIPMENT_CHARGES_ALIASES = {"shipmentcharges", "shipment_charges", "shippingcharges", "freightcharges"}
    _SHIPPING_ADDRESS_ALIASES = {"shippingaddress", "shipping_address", "deliveryaddress", "shiptoaddress"}

    # Line-level aliases (stored per line, not per order header)
    _LINE_LEVEL_ALIASES = (
        _ASIN_ALIASES
        | _QTY_ALIASES
        | _RATE_ALIASES
        | _TOTAL_ALIASES
        | _DISCOUNT_ALIASES
        | _TAX_ALIASES
        | _TITLE_ALIASES
        | _ORDER_DATE_ALIASES
    )

    # ─── Static helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _normalize_header(value):
        return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())

    @staticmethod
    def _to_string(value):
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        return str(value).strip()

    @staticmethod
    def _cell_to_raw_string(cell):
        """
        Read a cell value as its original text representation.
        For date/datetime cells, use the cell's number_format to reconstruct
        the original string (e.g. order IDs that Excel auto-formatted as dates).
        Falls back to ISO format if format is unknown.
        """
        value = cell.value
        if value is None:
            return ""
        if isinstance(value, datetime):
            # Try to detect if it's a date-only format
            fmt = (cell.number_format or "").lower()
            if "h" not in fmt and "s" not in fmt:
                return value.strftime("%Y-%m-%d")
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
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

    # ─── XLSX parsing ────────────────────────────────────────────────────────

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

        # Read cell objects (not values_only) so we can access number_format
        # for date cells that store Order IDs as dates
        cell_rows = list(sheet.iter_rows(values_only=False))
        if len(cell_rows) < 2:
            raise UserError(_("The XLSX file does not contain importable rows."))

        # Convert to value rows for easy access; keep cell_rows for raw string reads
        rows = [[cell.value for cell in row] for row in cell_rows]

        headers = [self._to_string(cell.value) for cell in (cell_rows[0] or [])]
        if not any(headers):
            raise UserError(_("Header row is empty in the uploaded file."))

        normalized_headers = {}
        for idx, header in enumerate(headers):
            normalized = self._normalize_header(header)
            if normalized:
                normalized_headers[normalized] = idx

        # Resolve column keys
        order_id_key = self._find_header(normalized_headers, self._ORDER_ID_ALIASES)
        order_date_key = self._find_header(normalized_headers, self._ORDER_DATE_ALIASES)
        customer_key = self._find_header(normalized_headers, self._CUSTOMER_ALIASES)
        company_key = self._find_header(normalized_headers, self._COMPANY_ALIASES)
        warehouse_key = self._find_header(normalized_headers, self._WAREHOUSE_ALIASES)
        asin_key = self._find_header(normalized_headers, self._ASIN_ALIASES)
        qty_key = self._find_header(normalized_headers, self._QTY_ALIASES)
        rate_key = self._find_header(normalized_headers, self._RATE_ALIASES)
        total_key = self._find_header(normalized_headers, self._TOTAL_ALIASES)
        discount_key = self._find_header(normalized_headers, self._DISCOUNT_ALIASES)
        tax_key = self._find_header(normalized_headers, self._TAX_ALIASES)
        title_key = self._find_header(normalized_headers, self._TITLE_ALIASES)
        invoice_amount_key = self._find_header(normalized_headers, self._INVOICE_AMOUNT_ALIASES)
        invoice_id_key = self._find_header(normalized_headers, self._INVOICE_ID_ALIASES)
        invoice_date_key = self._find_header(normalized_headers, self._INVOICE_DATE_ALIASES)
        shipment_id_key = self._find_header(normalized_headers, self._SHIPMENT_ID_ALIASES)
        shipment_date_key = self._find_header(normalized_headers, self._SHIPMENT_DATE_ALIASES)
        shipment_charges_key = self._find_header(normalized_headers, self._SHIPMENT_CHARGES_ALIASES)
        shipping_address_key = self._find_header(normalized_headers, self._SHIPPING_ADDRESS_ALIASES)

        if not order_id_key:
            raise UserError(_("Missing required column: Order ID."))
        if not asin_key:
            raise UserError(_("Missing required column: ASIN / Product Code."))
        if not qty_key:
            raise UserError(_("Missing required column: Quantity."))

        grouped_rows = defaultdict(list)
        for line_no, (row, cell_row) in enumerate(zip(rows[1:], cell_rows[1:]), start=2):
            if not row or all(cell in (None, "") for cell in row):
                continue

            def get_cell(key, _row=row):
                if key is None:
                    return None
                idx = normalized_headers.get(key)
                if idx is None or idx >= len(_row):
                    return None
                return _row[idx]

            def get_raw_cell(key, _cell_row=cell_row):
                """Get cell object for raw string conversion (handles date-typed cells)."""
                if key is None:
                    return None
                idx = normalized_headers.get(key)
                if idx is None or idx >= len(_cell_row):
                    return None
                return _cell_row[idx]

            # Use raw cell read for Order ID to avoid date-type cells converting to "2025-03-06 00:00:00"
            order_id_cell = get_raw_cell(order_id_key)
            order_id = self._cell_to_raw_string(order_id_cell) if order_id_cell is not None else ""
            if not order_id:
                raise UserError(_("Order ID is missing at row %s.") % line_no)

            qty = self._to_float(get_cell(qty_key), default=0.0)
            if qty <= 0:
                raise UserError(_("Quantity must be greater than 0 at row %s.") % line_no)

            total = self._to_float(get_cell(total_key), default=0.0) if total_key else 0.0
            rate = self._to_float(get_cell(rate_key), default=0.0) if rate_key else 0.0
            # Unit price: Total / Qty when Total present, else use Rate column
            if total and qty:
                price_unit = total / qty
            else:
                price_unit = rate

            discount = self._to_float(get_cell(discount_key), default=0.0) if discount_key else 0.0

            # Parse order date
            date_raw = get_cell(order_date_key) if order_date_key else None
            order_date = False
            if isinstance(date_raw, datetime):
                order_date = fields.Datetime.to_string(date_raw)
            elif isinstance(date_raw, date):
                order_date = fields.Datetime.to_string(datetime.combine(date_raw, datetime.min.time()))
            elif date_raw not in (None, ""):
                try:
                    order_date = fields.Datetime.to_string(fields.Datetime.to_datetime(str(date_raw)))
                except Exception:
                    order_date = False

            # Parse invoice date
            inv_date_raw = get_cell(invoice_date_key) if invoice_date_key else None
            invoice_date = False
            if isinstance(inv_date_raw, datetime):
                invoice_date = inv_date_raw.date()
            elif isinstance(inv_date_raw, date):
                invoice_date = inv_date_raw
            elif inv_date_raw not in (None, ""):
                try:
                    invoice_date = fields.Date.to_date(str(inv_date_raw))
                except Exception:
                    invoice_date = False

            # Build raw dict for extra info storage
            row_raw = {}
            for idx, header in enumerate(headers):
                if not header:
                    continue
                value = row[idx] if idx < len(row) else None
                row_raw[header] = self._to_string(value)

            grouped_rows[order_id].append({
                "line_no": line_no,
                "order_id": order_id,
                "order_date": order_date,
                "customer_name": self._to_string(get_cell(customer_key)) if customer_key else "",
                "company_str": self._to_string(get_cell(company_key)) if company_key else "",
                "warehouse_str": self._to_string(get_cell(warehouse_key)) if warehouse_key else "",
                "asin": self._to_string(get_cell(asin_key)),
                "qty": qty,
                "price_unit": price_unit,
                "discount": discount,
                "tax_name": self._to_string(get_cell(tax_key)) if tax_key else "",
                "title": self._to_string(get_cell(title_key)) if title_key else "",
                "invoice_amount": self._to_float(get_cell(invoice_amount_key), 0.0) if invoice_amount_key else 0.0,
                "invoice_id": self._to_string(get_cell(invoice_id_key)) if invoice_id_key else "",
                "invoice_date": invoice_date,
                "shipment_id": self._to_string(get_cell(shipment_id_key)) if shipment_id_key else "",
                "shipment_date": self._to_string(get_cell(shipment_date_key)) if shipment_date_key else "",
                "shipment_charges": self._to_float(get_cell(shipment_charges_key), 0.0) if shipment_charges_key else 0.0,
                "shipping_address": self._to_string(get_cell(shipping_address_key)) if shipping_address_key else "",
                "raw": row_raw,
            })

        if not grouped_rows:
            raise UserError(_("No valid import lines found in the uploaded file."))

        return grouped_rows

    # ─── Lookup helpers ──────────────────────────────────────────────────────

    def _get_or_create_customer(self, customer_name):
        if not customer_name or not str(customer_name).strip():
            customer_name = "E-com Customer"
        customer_name = str(customer_name).strip()
        partner = self.env["res.partner"].sudo().search([("name", "=ilike", customer_name)], limit=1)
        if partner:
            if getattr(partner, "customer_rank", 0) < 1:
                partner.sudo().with_context(bypass_approval=True).write({"customer_rank": 1})
            return partner
        create_vals = {
            "name": customer_name,
            "company_type": "company",
            "customer_rank": 1,
        }
        # ks_contact approval bypass — same pattern as purchase vendor creation
        for field in ("is_customer", "customer_type", "created_for_ecom", "approval_status", "is_approved"):
            if field in self.env["res.partner"]._fields:
                if field == "is_customer":
                    create_vals[field] = True
                elif field == "customer_type":
                    create_vals[field] = "operational"
                elif field == "created_for_ecom":
                    create_vals[field] = True
                elif field == "approval_status":
                    create_vals[field] = "approved"
                elif field == "is_approved":
                    create_vals[field] = True
        return (
            self.env["res.partner"]
            .sudo()
            .with_context(bypass_approval=True)
            .create(create_vals)
        )

    @staticmethod
    def _parse_company_branch(company_str):
        if not company_str or not str(company_str).strip():
            return ("", None)
        parts = str(company_str).strip().split("-", 1)
        company_name = parts[0].strip() if parts[0] else ""
        branch_name = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        return (company_name, branch_name)

    def _get_company_by_name(self, company_name):
        if not company_name or not str(company_name).strip():
            return self.env["res.company"]
        name = str(company_name).strip()
        company = self.env["res.company"].search([("name", "=", name)], limit=1)
        if company:
            return company
        return self.env["res.company"].search([("name", "=ilike", name)], limit=1)

    def _get_warehouse_by_name(self, warehouse_name, company_id=None):
        if not warehouse_name or not str(warehouse_name).strip():
            return self.env["stock.warehouse"]
        name = str(warehouse_name).strip()
        domain = [("name", "=ilike", name)]
        if company_id:
            domain.append(("company_id", "=", company_id))
        return self.env["stock.warehouse"].search(domain, limit=1)

    def _get_product_by_asin(self, asin):
        if not asin or not str(asin).strip():
            return self.env["product.product"]
        return self.env["product.product"].search(
            [("default_code", "=", str(asin).strip())],
            limit=1,
        )

    def _get_tax_by_name(self, tax_name, company):
        """
        Find sale tax by name or percentage.
        Tries: exact name → ilike name → numeric percentage match.
        Returns recordset or empty.
        """
        if not tax_name:
            return self.env["account.tax"]
        tax_name = str(tax_name).strip()
        base_domain = [("type_tax_use", "=", "sale"), ("company_id", "=", company.id)]

        # 1. Exact match
        tax = self.env["account.tax"].search([("name", "=", tax_name)] + base_domain, limit=1)
        if tax:
            return tax
        # 2. Case-insensitive match
        tax = self.env["account.tax"].search([("name", "=ilike", tax_name)] + base_domain, limit=1)
        if tax:
            return tax
        # 3. Numeric percentage (e.g. "18" or "18%" or "18.0")
        try:
            amount = float(tax_name.replace("%", "").strip())
            tax = self.env["account.tax"].search(
                [("amount", "=", amount), ("amount_type", "=", "percent")] + base_domain,
                limit=1,
            )
            if tax:
                return tax
        except (ValueError, AttributeError):
            pass
        return self.env["account.tax"]

    def _get_product_taxes(self, product, company):
        """Return the product's default sale taxes filtered to the given company."""
        return product.taxes_id.filtered(
            lambda t: t.company_id == company and t.type_tax_use == "sale"
        )

    def _prepare_extra_info_commands(self, sample_row):
        """Store all columns (except order/line-level columns) as key-value info."""
        excluded_keys = self._ORDER_ID_ALIASES | self._LINE_LEVEL_ALIASES
        commands = []
        for key, value in sample_row.items():
            normalized_key = self._normalize_header(key)
            if not normalized_key or normalized_key in excluded_keys:
                continue
            if value in (None, ""):
                continue
            commands.append(
                Command.create({
                    "field_key": key,
                    "field_value": self._to_string(value),
                })
            )
        return commands

    # ─── Toast notification builder ──────────────────────────────────────────

    def _build_toast_notification(self, failed_lines, created_orders, total_lines_created, import_errors=None):
        import_errors = import_errors or []
        failed_count = len(failed_lines)
        success_payload = None
        failed_payload = None
        errors_payload = None

        if import_errors:
            error_list = "; ".join(e["reason"] for e in import_errors[:5])
            if len(import_errors) > 5:
                error_list += _(" and %s more") % (len(import_errors) - 5)
            errors_payload = {
                "title": _("SO Import: Validation failed"),
                "message": _("Order(s) skipped: %s") % error_list,
                "type": "danger",
            }

        if created_orders:
            success_payload = {
                "title": _("SO Import: Success"),
                "message": _("Created: %(so_count)s Sale Order(s), %(line_count)s line(s).") % {
                    "so_count": len(created_orders),
                    "line_count": total_lines_created,
                },
                "type": "success",
            }

        if failed_count:
            failed_asin_list = ", ".join(item["asin"] for item in failed_lines[:10])
            if failed_count > 10:
                failed_asin_list += _(" and %s more") % (failed_count - 10)
            failed_payload = {
                "title": _("SO Import: Records not created"),
                "message": _("ASIN(s) not found (no matching product): %s") % failed_asin_list,
                "type": "danger",
            }
        elif not created_orders and not import_errors:
            success_payload = {
                "title": _("SO Import"),
                "message": _("No lines imported. Ensure ASINs match product Internal References."),
                "type": "warning",
            }

        return {"success": success_payload, "failed": failed_payload, "errors": errors_payload}

    # ─── Main import action ──────────────────────────────────────────────────

    def action_import_sale_orders(self):
        self.ensure_one()
        grouped_rows = self._extract_sheet_data()

        ecom_tag = self.env["ks.ecom.tag"].sudo().search([("name", "=", "E-com")], limit=1)
        if not ecom_tag:
            ecom_tag = self.env["ks.ecom.tag"].sudo().create({"name": "E-com"})

        created_orders = self.env["sale.order"]
        failed_lines = []
        import_errors = []
        invoice_failures = []
        total_lines_created = 0

        for order_id, order_rows in grouped_rows.items():
            # ── Validate ASINs ──
            valid_rows = []
            for row in order_rows:
                asin = row.get("asin") or ""
                if not asin.strip():
                    failed_lines.append({"asin": _("(empty)"), "order_id": order_id, "line_no": row["line_no"]})
                    continue
                product = self._get_product_by_asin(asin)
                if not product:
                    failed_lines.append({"asin": asin, "order_id": order_id, "line_no": row["line_no"]})
                    continue
                valid_rows.append((row, product))

            if not valid_rows:
                continue

            # ── Duplicate order ID check ──
            existing_so = self.env["sale.order"].search(
                [("ks_ecom_order_id", "=", order_id)], limit=1
            )
            if existing_so:
                import_errors.append({
                    "order_id": order_id,
                    "reason": _("Order ID %s already exists.") % order_id,
                })
                continue

            # ── Company & Warehouse resolution ──
            first_row = order_rows[0]
            company_str = first_row.get("company_str") or ""
            warehouse_str = first_row.get("warehouse_str") or ""

            if not company_str.strip():
                import_errors.append({
                    "order_id": order_id,
                    "reason": _("Order %s: Company not found (empty Company column).") % order_id,
                })
                continue

            company_name, _branch = self._parse_company_branch(company_str)
            if not company_name:
                import_errors.append({
                    "order_id": order_id,
                    "reason": _("Order %s: Company not found (no company name before hyphen).") % order_id,
                })
                continue

            company = self._get_company_by_name(company_name)
            if not company:
                import_errors.append({
                    "order_id": order_id,
                    "reason": _("Order %s: Company not found: '%s'.") % (order_id, company_name),
                })
                continue

            if not warehouse_str.strip():
                import_errors.append({
                    "order_id": order_id,
                    "reason": _("Order %s: Warehouse not found (empty Warehouse column).") % order_id,
                })
                continue

            warehouse = self._get_warehouse_by_name(warehouse_str, company_id=company.id)
            if not warehouse:
                import_errors.append({
                    "order_id": order_id,
                    "reason": _("Order %s: Warehouse not found: '%s'.") % (order_id, warehouse_str.strip()),
                })
                continue

            if warehouse.company_id != company:
                import_errors.append({
                    "order_id": order_id,
                    "reason": _("Warehouse and Company mismatch for Order ID %s.") % order_id,
                })
                continue

            # ── Customer ──
            customer_name = (first_row.get("customer_name") or "").strip() or "E-com Customer"
            customer = self._get_or_create_customer(customer_name)

            # ── Create Sale Order ──
            so_date = first_row.get("order_date") or fields.Datetime.now()
            so_vals = {
                "partner_id": customer.id,
                "company_id": company.id,
                "warehouse_id": warehouse.id,
                "date_order": so_date,
                "origin": _("E-com Import - %s") % order_id,
                "ks_ecom_imported": True,
                "ks_ecom_order_id": order_id,
                "ks_ecom_source_file": self.file_name,
                "ks_ecom_tag_ids": [Command.link(ecom_tag.id)],
                "ks_ecom_info_ids": self._prepare_extra_info_commands(first_row["raw"]),
            }
            sale_order = (
                self.env["sale.order"]
                .sudo()
                .with_company(company)
                .with_context(bypass_approval=True)
                .create(so_vals)
            )

            # ── Create Order Lines ──
            for row, product in valid_rows:
                line_name = (
                    row["title"]
                    or product.name
                    or product.display_name
                    or row["asin"]
                    or _("Product")
                )
                # Resolve tax:
                # 1. Try to find from Excel TAX column
                # 2. Fallback to product's default sale tax
                # (programmatic create does not trigger onchange, so we must set explicitly)
                tax = self._get_tax_by_name(row["tax_name"], company)
                if not tax:
                    tax = self._get_product_taxes(product, company)

                line_vals = {
                    "order_id": sale_order.id,
                    "product_id": product.id,
                    "name": line_name,
                    "product_uom_qty": row["qty"],
                    "price_unit": row["price_unit"],
                    "discount": row["discount"],
                    "tax_id": [Command.set(tax.ids)],
                }
                self.env["sale.order.line"].sudo().with_context(bypass_approval=True).create(line_vals)
                total_lines_created += 1

            # ── Confirm Sale Order ──
            sale_order.sudo().action_confirm()

            # ── Mark outgoing delivery with ks_ecom_order_id ──
            # Stored directly so delivery import wizard can match by this field.
            if sale_order.picking_ids:
                outgoing = sale_order.picking_ids.filtered(
                    lambda p: p.picking_type_id.code == "outgoing"
                )
                if outgoing:
                    outgoing.write({"ks_ecom_order_id": order_id})

            # ── Auto-create Customer Invoice ──
            try:
                sale_order._create_invoices()
                sale_order.invalidate_recordset(["invoice_ids"])
                for inv in sale_order.invoice_ids:
                    if not inv.invoice_date:
                        # Use invoice_date from sheet if available, else today
                        inv_date = first_row.get("invoice_date") or fields.Date.context_today(self)
                        inv.invoice_date = inv_date
            except Exception as e:
                _logger.warning(
                    "Invoice creation failed for SO %s (Order ID: %s): %s",
                    sale_order.name,
                    order_id,
                    e,
                    exc_info=True,
                )
                invoice_failures.append((sale_order.name, str(e)))

            created_orders |= sale_order

        # ── Send bus notifications ──
        toasts = self._build_toast_notification(
            failed_lines, created_orders, total_lines_created, import_errors=import_errors
        )
        bus = self.env["bus.bus"]
        partner_id = self.env.user.partner_id

        if toasts["errors"]:
            bus._sendone(partner_id, "simple_notification", {
                "type": toasts["errors"]["type"],
                "title": toasts["errors"]["title"],
                "message": toasts["errors"]["message"],
                "sticky": True,
            })
        if toasts["failed"]:
            bus._sendone(partner_id, "simple_notification", {
                "type": toasts["failed"]["type"],
                "title": toasts["failed"]["title"],
                "message": toasts["failed"]["message"],
                "sticky": True,
            })
        if toasts["success"]:
            bus._sendone(partner_id, "simple_notification", {
                "type": toasts["success"]["type"],
                "title": toasts["success"]["title"],
                "message": toasts["success"]["message"],
                "sticky": True,
            })
        if invoice_failures:
            failure_list = "; ".join(
                _("%(so)s: %(reason)s") % {"so": so_name, "reason": reason}
                for so_name, reason in invoice_failures[:5]
            )
            if len(invoice_failures) > 5:
                failure_list += _(" and %s more") % (len(invoice_failures) - 5)
            bus._sendone(partner_id, "simple_notification", {
                "type": "warning",
                "title": _("SO Import: Invoice could not be created"),
                "message": _(
                    "Sale Order(s) were confirmed but the following could not be invoiced: %s"
                ) % failure_list,
                "sticky": True,
            })

        if not created_orders:
            return {"type": "ir.actions.act_window_close"}

        if len(created_orders) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Sale Order"),
                "res_model": "sale.order",
                "view_mode": "form",
                "res_id": created_orders.id,
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Imported Sale Orders"),
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("id", "in", created_orders.ids)],
            "target": "current",
        }
