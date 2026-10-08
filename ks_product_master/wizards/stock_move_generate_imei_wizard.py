# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class StockMoveGenerateImeiWizard(models.TransientModel):
    _name = "stock.move.generate.imei.wizard"
    _description = "Generate IMEI Wizard"

    move_id = fields.Many2one("stock.move", string="Stock Move", required=True, ondelete="cascade")
    prefix = fields.Char(
        string="Prefix Number",
        required=False,
        help="Optional numeric prefix or starting 15-digit IMEI number. If left empty, an automatic company-wise unique sequence is used."
    )
    is_imei1 = fields.Boolean(string="IMEI 1", default=True)
    is_imei2 = fields.Boolean(string="IMEI 2", default=False)
    is_dual_sim = fields.Boolean(string="Is Dual SIM", compute="_compute_is_dual_sim")

    @api.depends("move_id", "move_id.show_IMEI_field2", "move_id.is_product_dual_sim")
    def _compute_is_dual_sim(self):
        for rec in self:
            rec.is_dual_sim = bool(
                rec.move_id
                and (rec.move_id.show_IMEI_field2 or getattr(rec.move_id, "is_product_dual_sim", False))
            )

    def _get_or_create_company_sequence(self, company):
        """Fetch or automatically initialize a company-specific ir.sequence for IMEI generation
        configured with a 5-digit prefix and 10-digit padding (15 digits total)."""
        Sequence = self.env["ir.sequence"].sudo()
        domain = [("code", "=", "stock.move.generate.imei")]
        if company:
            domain.append(("company_id", "=", company.id))
        else:
            domain.append(("company_id", "=", False))

        seq = Sequence.search(domain, limit=1)
        if not seq:
            # Check for a global sequence record to inherit prefix/padding from
            global_seq = Sequence.search([("code", "=", "stock.move.generate.imei"), ("company_id", "=", False)], limit=1)
            default_prefix = global_seq.prefix if (global_seq and global_seq.prefix) else False
            if not default_prefix:
                if company and company.id and company.id != 1:
                    default_prefix = f"333{company.id:02d}"
                else:
                    default_prefix = "33333"

            seq = Sequence.create({
                "name": f"IMEI Generation Sequence ({company.name})" if company else "IMEI Generation Sequence",
                "code": "stock.move.generate.imei",
                "prefix": default_prefix,
                "padding": 10,
                "number_next": 1,
                "number_increment": 1,
                "company_id": company.id if company else False,
            })
        return seq

    def _get_unique_seq_imei(self, seq, used_in_batch=None):
        """Fetch the next 15-digit IMEI from the sequence, automatically skipping any
        numbers that already exist in stock.quant or stock.move.line to guarantee uniqueness."""
        while True:
            raw = seq.next_by_id()
            clean = "".join(c for c in (raw or "") if c.isdigit())
            if len(clean) < 15:
                clean = clean.zfill(15)
            elif len(clean) > 15:
                clean = clean[-15:]

            if used_in_batch is not None and clean in used_in_batch:
                continue

            quant_exists = self.env["stock.quant"].sudo().search_count([
                "|", ("imei", "=", clean), ("imei2", "=", clean)
            ])
            if quant_exists:
                continue

            line_exists = self.env["stock.move.line"].sudo().search_count([
                "|", ("imei", "=", clean), ("imei2", "=", clean)
            ])
            if line_exists:
                continue

            if used_in_batch is not None:
                used_in_batch.add(clean)
            return clean

    def action_generate(self):
        self.ensure_one()
        if not self.is_imei1 and not self.is_imei2:
            raise ValidationError(_("Please select at least one option: IMEI 1 or IMEI 2."))

        has_user_prefix = bool(self.prefix and self.prefix.strip())
        clean_prefix = "".join(c for c in (self.prefix or "") if c.isdigit()) if has_user_prefix else ""
        if has_user_prefix and not clean_prefix:
            raise ValidationError(_("Please enter a valid numeric prefix (e.g. 86420 or 33333) or leave the field blank to use auto-sequence."))

        lines = self.move_id.move_line_ids
        if not lines:
            count = int(self.move_id.product_uom_qty or 1)
            if count <= 0:
                count = 1
            default_vals = {
                "move_id": self.move_id.id,
                "product_id": self.move_id.product_id.id,
                "location_id": self.move_id.location_id.id,
                "location_dest_id": self.move_id.location_dest_id.id,
                "product_uom_id": self.move_id.product_uom.id,
                "quantity": 1,
                "company_id": self.move_id.company_id.id if self.move_id.company_id else False,
            }
            if self.move_id.picking_id:
                default_vals["picking_id"] = self.move_id.picking_id.id
            if self.move_id.made_in_country_id:
                default_vals["made_in_country_id"] = self.move_id.made_in_country_id.id
            new_lines = []
            for line_idx in range(count):
                new_lines.append(self.env["stock.move.line"].create(default_vals))
            lines = self.move_id.move_line_ids

        total_lines = len(lines)
        if total_lines == 0:
            raise UserError(_("No move lines found to generate IMEI for."))

        both_checked = self.is_imei1 and (self.is_imei2 and self.is_dual_sim)
        used_in_batch = set()

        if not clean_prefix:
            # Case 1: No prefix provided -> Use company-wise unique ir.sequence (5-digit prefix + 10-digit sequence = 15 digits)
            company = self.move_id.company_id or self.env.company
            seq = self._get_or_create_company_sequence(company)
            for line in lines:
                vals_to_write = {}
                if both_checked:
                    vals_to_write["imei"] = self._get_unique_seq_imei(seq, used_in_batch)
                    vals_to_write["imei2"] = self._get_unique_seq_imei(seq, used_in_batch)
                else:
                    if self.is_imei1:
                        vals_to_write["imei"] = self._get_unique_seq_imei(seq, used_in_batch)
                    if self.is_imei2 and self.is_dual_sim:
                        vals_to_write["imei2"] = self._get_unique_seq_imei(seq, used_in_batch)
                if vals_to_write:
                    line.write(vals_to_write)
        else:
            # Case 2: Manual prefix provided -> format to 15 digits based on prefix
            if len(clean_prefix) >= 15:
                start_num = int(clean_prefix[:15])
                def get_imei_val(offset):
                    return str(start_num + offset).zfill(15)
            else:
                pad = 15 - len(clean_prefix)
                def get_imei_val(offset):
                    return f"{clean_prefix}{str(offset + 1).zfill(pad)}"

            for i, line in enumerate(lines):
                vals_to_write = {}
                if both_checked:
                    vals_to_write["imei"] = get_imei_val(2 * i)
                    vals_to_write["imei2"] = get_imei_val(2 * i + 1)
                else:
                    if self.is_imei1:
                        vals_to_write["imei"] = get_imei_val(i)
                    if self.is_imei2 and self.is_dual_sim:
                        vals_to_write["imei2"] = get_imei_val(i)
                if vals_to_write:
                    line.write(vals_to_write)

        return {
            "name": _("Detailed Operations"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "stock.move",
            "views": [(self.env.ref("stock.view_stock_move_operations").id, "form")],
            "view_id": self.env.ref("stock.view_stock_move_operations").id,
            "target": "new",
            "res_id": self.move_id.id,
            "context": dict(self.env.context),
        }
