# -*- coding: utf-8 -*-
import base64
import logging
import re
from collections import defaultdict
from io import BytesIO

from odoo import _, fields, models
from odoo.exceptions import UserError

try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None

_logger = logging.getLogger(__name__)


class KsPoRefundImportWizard(models.TransientModel):
    _name = "ks.po.refund.import.wizard"
    _description = "Purchase Order Refund Import Wizard (E-com)"

    file_data = fields.Binary(string="XLSX File")
    file_name = fields.Char(string="File Name")

    def action_download_template(self):
        return {
            "type": "ir.actions.act_url",
            "url": "/ks_ecom_purchase/static/src/xls/po_refund_import_template.xlsx",
            "target": "self",
        }

    _ORDER_ID_ALIASES = {"orderid", "order_id", "orderno", "order_no", "ecomorderid"}
    _PRODUCT_CODE_ALIASES = {"asin", "sku", "productcode", "defaultcode", "internalreference", "barcode"}
    _QTY_ALIASES = {"orderquantity", "qty", "quantity", "refundqty", "returnqty", "quantitytoreturn", "qtytoreturn", "reversalitemqty", "reversalitemquantity"}

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
        self.ensure_one()
        if load_workbook is None:
            raise UserError(_("Python package 'openpyxl' is required to import XLSX files."))

        if not self.file_data or not self.file_name:
            raise UserError(_("Please upload an XLSX file before importing."))

        if not self.file_name.lower().endswith(".xlsx"):
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
        qty_key = self._find_header(normalized_headers, self._QTY_ALIASES)

        if not order_id_key:
            raise UserError(_("Missing required column: Order ID."))
        if not asin_key:
            raise UserError(_("Missing required column: ASIN/Product Code."))
        if not qty_key:
            raise UserError(_("Missing required column: Quantity (refund quantity)."))

        refund_data = []
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
            qty = self._to_float(get_cell(qty_key), default=0.0)

            if not order_id:
                raise UserError(_("Order ID is missing at row %s.") % line_no)
            if not asin:
                raise UserError(_("ASIN is missing at row %s.") % line_no)
            if qty <= 0:
                raise UserError(_("Refund quantity must be greater than 0 at row %s.") % line_no)

            refund_data.append({
                "line_no": line_no,
                "order_id": order_id,
                "asin": asin,
                "quantity": qty,
            })

        if not refund_data:
            raise UserError(_("No valid import lines found in the uploaded file."))

        return refund_data

    def action_import_refund_data(self):
        """Cancel non-done receipts, create return pickings for done receipts,
        reverse posted vendor bills, and mark PO as refunded.
        """
        self.ensure_one()
        refund_data = self._extract_sheet_data()

        # Group by order_id; aggregate quantity per (order_id, asin)
        grouped = defaultdict(lambda: defaultdict(float))
        for row in refund_data:
            grouped[row["order_id"]][row["asin"]] += row["quantity"]

        ReturnWizard = self.env["stock.return.picking"]
        created_count = 0
        credits_created = 0
        skipped_count = 0
        warnings = []

        for order_id, asin_qty in grouped.items():
            # Find PO by order_id (origin or ks_ecom_order_id)
            po = self.env["purchase.order"].search([
                "|",
                ("ks_ecom_order_id", "=", order_id),
                ("origin", "ilike", order_id),
                ("state", "in", ("purchase", "done")),
            ], limit=1)
            if not po:
                po_ecom = self.env["purchase.order"].search([
                    ("ks_ecom_order_id", "=", order_id),
                    ("ks_ecom_order_id", "!=", False),
                ], limit=1)
                if po_ecom:
                    po = po_ecom

            if not po:
                warnings.append(_("Order ID '%s' not found in Purchase Orders.") % order_id)
                skipped_count += len(asin_qty)
                continue

            # Strict payment validation: only process refund if original bill(s) are
            # posted, have payment_state 'paid', and have at least one linked account.payment
            po.invalidate_recordset(["invoice_ids"])
            posted_bills = po.invoice_ids.filtered(
                lambda m: m.state == "posted" and m.move_type == "in_invoice"
            )
            if posted_bills:
                bills_not_eligible = posted_bills.filtered(
                    lambda m: m.payment_state != "in_payment"
                    or not (m.reconciled_payment_ids or m.matched_payment_ids)
                )
                if bills_not_eligible:
                    warnings.append(
                        _(
                            "Order ID %s refund could not be process because Bill  "
                            "payment is not 'Paid'. first complete the  payment."
                        )
                        % order_id
                    )
                    skipped_count += len(asin_qty)
                    continue

            try:
                # 1) Cancel receipts (pickings) that are NOT in 'cancel' or 'done'
                to_cancel = po.picking_ids.filtered(
                    lambda p: p.state not in ("cancel", "done")
                )
                for picking in to_cancel:
                    try:
                        picking.action_cancel()
                    except Exception as cancel_exc:
                        _logger.warning(
                            "Could not cancel picking %s for Order ID %s: %s",
                            picking.name,
                            order_id,
                            cancel_exc,
                            exc_info=True,
                        )
                        warnings.append(
                            _("Order ID '%s': could not cancel receipt %s: %s")
                            % (order_id, picking.name, cancel_exc)
                        )

                # 2) For done receipt: create Return Picking (standard Odoo flow)
                receipt = po.picking_ids.filtered(
                    lambda p: p.picking_type_id.code == "incoming" and p.state == "done"
                ).sorted("create_date", reverse=True)[:1]

                if receipt:
                    receipt = receipt[0]
                    if receipt._can_return():
                        wizard = ReturnWizard.with_context(
                            active_id=receipt.id,
                            active_model="stock.picking",
                        ).create({"picking_id": receipt.id})

                        if wizard.product_return_moves:
                            for asin, qty in asin_qty.items():
                                product = self.env["product.product"].search(
                                    [("default_code", "=", asin)], limit=1
                                )
                                if not product:
                                    warnings.append(
                                        _("Product with ASIN '%s' not found (Order ID: %s).")
                                        % (asin, order_id)
                                    )
                                    skipped_count += 1
                                    continue

                                line = wizard.product_return_moves.filtered(
                                    lambda l: l.product_id.id == product.id and l.move_id
                                )[:1]
                                if not line:
                                    warnings.append(
                                        _("ASIN '%s' not found on receipt for Order ID '%s'.")
                                        % (asin, order_id)
                                    )
                                    skipped_count += 1
                                    continue

                                max_qty = line.move_id.quantity
                                if qty > max_qty:
                                    warnings.append(
                                        _(
                                            "Refund qty %s for ASIN '%s' (Order ID: %s) exceeds receipt qty %s; using %s."
                                        )
                                        % (qty, asin, order_id, max_qty, max_qty)
                                    )
                                    qty = max_qty
                                line.quantity = qty

                            if any(
                                line.quantity > 0 for line in wizard.product_return_moves
                            ):
                                try:
                                    action = wizard.action_create_returns()
                                    return_picking_id = action.get("res_id")
                                    if return_picking_id:
                                        self.env["stock.picking"].browse(
                                            return_picking_id
                                        ).write({"is_ecom_refund": True})
                                        created_count += 1
                                except Exception as e:
                                    warnings.append(
                                        _("Order ID '%s': could not create return: %s")
                                        % (order_id, str(e))
                                    )
                            else:
                                warnings.append(
                                    _("No positive quantities to return for Order ID '%s'.")
                                    % order_id
                                )
                        else:
                            warnings.append(
                                _("No returnable moves for Order ID '%s' (receipt %s).")
                                % (order_id, receipt.name)
                            )
                    else:
                        _logger.info(
                            "Receipt %s for Order ID '%s' cannot be returned.",
                            receipt.name,
                            order_id,
                        )
                        warnings.append(
                            _("Receipt %s for Order ID '%s' cannot be returned (must be Done).")
                            % (receipt.name, order_id)
                        )
                else:
                    _logger.info(
                        "No done receipt for Order ID '%s' (PO: %s); skipping return.",
                        order_id,
                        po.name,
                    )

                # 3) Reverse posted Vendor Bills (create Credit Notes)
                po.invalidate_recordset(["invoice_ids"])
                posted_bills = po.invoice_ids.filtered(
                    lambda m: m.state == "posted" and m.move_type == "in_invoice"
                )
                refund_date = fields.Date.context_today(self)
                for bill in posted_bills:
                    try:
                        default_vals = {
                            "invoice_date": refund_date,
                            "date": refund_date,
                        }
                        reverse_moves = bill._reverse_moves(
                            default_values_list=[default_vals],
                            cancel=True,
                        )
                        if reverse_moves:
                            credits_created += len(reverse_moves)
                    except Exception as rev_exc:
                        _logger.warning(
                            "Vendor bill reversal failed for PO %s (Order ID: %s), bill %s: %s",
                            po.name,
                            order_id,
                            bill.name,
                            rev_exc,
                            exc_info=True,
                        )
                        warnings.append(
                            _("Order ID '%s': could not reverse bill %s: %s")
                            % (order_id, bill.name, rev_exc)
                        )

                # 4) Mark PO as refunded
                po.ks_ecom_refunded = True

            except Exception as e:
                _logger.warning(
                    "Refund processing failed for Order ID '%s' (PO: %s): %s",
                    order_id,
                    po.name,
                    e,
                    exc_info=True,
                )
                warnings.append(
                    _("Order ID '%s': refund processing failed: %s") % (order_id, e)
                )
                skipped_count += len(asin_qty)

        # Same message style as PO Import: red box for records not created/skipped, green box for success
        bus = self.env["bus.bus"]
        partner_id = self.env.user.partner_id

        # Red box: warnings / records not created
        if warnings:
            warning_list = "; ".join(warnings[:10])
            if len(warnings) > 10:
                warning_list += _(" (and %s more)") % (len(warnings) - 10)
            bus._sendone(
                partner_id,
                "simple_notification",
                {
                    "type": "danger",
                    "title": _("Refund Import: Records not created"),
                    "message": warning_list,
                    "sticky": True,
                },
            )

        # Green box: success summary
        if created_count > 0 or credits_created > 0:
            parts = []
            if created_count > 0:
                parts.append(_("%s return(s)") % created_count)
            if credits_created > 0:
                parts.append(_("%s credit note(s)") % credits_created)
            bus._sendone(
                partner_id,
                "simple_notification",
                {
                    "type": "success",
                    "title": _("Refund Import: Success"),
                    "message": _("Created: %s.") % ", ".join(parts),
                    "sticky": True,
                },
            )
        elif not warnings:
            bus._sendone(
                partner_id,
                "simple_notification",
                {
                    "type": "warning",
                    "title": _("Refund Import"),
                    "message": _("No returns were created. Check file format and data."),
                    "sticky": True,
                },
            )

        return {"type": "ir.actions.act_window_close"}
