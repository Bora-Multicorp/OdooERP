# -- coding: utf-8 --
import base64
import io
from odoo.exceptions import ValidationError, UserError
from odoo import models, fields, api, _

try:
    import openpyxl
except ImportError:
    openpyxl = None


class StockMove(models.Model):
    _inherit = 'stock.move'

    hide_imei_fields = fields.Boolean(
        compute='_compute_show_imei_column',
        store=False, tracking=True
    )

    @api.depends('has_tracking', 'picking_type_id.use_create_lots', 'picking_type_id.use_existing_lots', 'product_id', 'origin_returned_move_id', 'state')
    def _compute_display_assign_serial(self):
        for move in self:
            move.display_import_lot = (
                move.has_tracking != 'none'
                and move.product_id
                and (move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots)
                and not move.origin_returned_move_id.id
                and move.state not in ('done', 'cancel')
            )
            move.display_assign_serial = move.display_import_lot

    @api.depends('product_id.is_mobile_category_selected')
    def _compute_show_imei_column(self):
        for move in self:
            # Mirrors product.template.is_mobile_category_selected (category or any ancestor flagged as mobile)
            move.hide_imei_fields = move.product_id.is_mobile_category_selected

    show_IMEI_field = fields.Boolean(string='Show IMEI Field 1', compute='_compute_show_imei_fields')
    show_IMEI_field2 = fields.Boolean(string='Show IMEI Field 2', compute='_compute_show_imei_fields')

    def _compute_show_imei_fields(self):
        for rec in self:
            if rec.product_id.is_mobile_category_selected:
                rec.show_IMEI_field = True
                rec.show_IMEI_field2 = rec.product_id.is_dual_sim
            else:
                rec.show_IMEI_field = False
                rec.show_IMEI_field2 = False

    specs_made = fields.Many2one(
        'res.country',
        string='Spec Made For',
        help='Specification made for a specific country.',
        tracking=True
    )

    made_country = fields.Many2one(
        'res.country',
        string='Made In',
        help='Country where the product is manufactured',
        tracking=True
    )

    # Computed from move lines so the Operations tab column auto-fills when lines have a country.
    made_in_country_id = fields.Many2one(
        'res.country',
        string='Made In Country',
        compute='_compute_made_in_country_id',
        store=True,
        readonly=False,
        help='Country of origin. Auto-filled from move lines.',
    )

    @api.depends('move_line_ids.made_in_country_id')
    def _compute_made_in_country_id(self):
        for move in self:
            line = move.move_line_ids.filtered(lambda l: l.made_in_country_id)[:1]
            if line:
                move.made_in_country_id = line.made_in_country_id
            else:
                move.made_in_country_id = move._origin.made_in_country_id

    @api.model_create_multi
    def create(self, vals_list):
        """Override to propagate specs_made and made_country from picking to moves"""
        moves = super().create(vals_list)
        for move in moves:
            # If move is linked to a picking, inherit country fields from picking
            if move.picking_id and (move.picking_id.specs_made or move.picking_id.made_country):
                if move.picking_id.specs_made and not move.specs_made:
                    move.specs_made = move.picking_id.specs_made.id
                if move.picking_id.made_country and not move.made_country:
                    move.made_country = move.picking_id.made_country.id
        return moves

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        """Override to propagate specs_made and made_country to move lines"""
        vals = super()._prepare_move_line_vals(quantity, reserved_quant)
        if self.specs_made:
            vals['specs_made'] = self.specs_made.id
        if self.made_country:
            vals['made_country'] = self.made_country.id
        return vals

    def _action_assign(self, force_qty=False):
        """Override to set context for filtering quants by specs_made and made_country"""
        # Set context with country fields so _gather can filter quants
        context_updates = {}
        if self.specs_made:
            context_updates['filter_specs_made'] = self.specs_made.id
        if self.made_country:
            context_updates['filter_made_country'] = self.made_country.id
        
        if context_updates:
            return super(StockMove, self.with_context(**context_updates))._action_assign(force_qty=force_qty)
        else:
            return super()._action_assign(force_qty=force_qty)

    def _update_reserved_quantity_vals(self, need, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
        """Override to filter quants based on specs_made and made_country"""
        # Pass specs_made and made_country in context so _gather can filter quants
        context_updates = {}
        if self.specs_made:
            context_updates['filter_specs_made'] = self.specs_made.id
        if self.made_country:
            context_updates['filter_made_country'] = self.made_country.id
        
        if context_updates:
            move_line_vals, taken_quantity = super(StockMove, self.with_context(**context_updates))._update_reserved_quantity_vals(
                need, location_id, lot_id, package_id, owner_id, strict
            )
        else:
            move_line_vals, taken_quantity = super()._update_reserved_quantity_vals(need, location_id, lot_id, package_id, owner_id, strict)
        
        return move_line_vals, taken_quantity

    @api.onchange('made_in_country_id')
    def _onchange_made_in_country_id_fill_lines(self):
        """When Made In Country is set on the stock.move popup, bulk-fill all
        move lines so each Lot/Serial row shows the same country immediately."""
        for move in self:
            if not move.made_in_country_id:
                continue
            for line in move.move_line_ids:
                line.made_in_country_id = move.made_in_country_id

    def write(self, vals):
        res = super().write(vals)
        if 'made_in_country_id' in vals and vals['made_in_country_id']:
            if not self.env.context.get('skip_line_cascade'):
                for move in self:
                    move.move_line_ids.write({'made_in_country_id': vals['made_in_country_id']})
        return res

    def _action_done(self, cancel_backorder=False):
        """After standard validation, write made_country / specs_made onto the quants
        that Odoo created or updated for every done move line.

        This covers non-lot-tracked products that the existing
        stock_quant_inherit.create (which relies on lot_id) would otherwise miss.
        For lot-tracked products it is a harmless no-op when the quant create
        already set the fields.
        """
        res = super()._action_done(cancel_backorder=cancel_backorder)
        for move in self:
            if move.state != 'done':
                continue
            picking = move.picking_id
            for line in move.move_line_ids:
                # Resolution order (most specific wins):
                # 1. move line  — explicit per-line value, e.g. Anguilla
                # 2. move header — set at move level
                # 3. picking header — e.g. India set on the receipt form
                # The picking header is only a fallback; it never overrides a
                # more-specific value already set on the line or move.
                made_country = (
                    line.made_country
                    or move.made_country
                    or move.made_in_country_id
                    or (picking and picking.made_country)
                )
                specs_made = line.specs_made or move.specs_made or (picking and picking.specs_made)
                if not made_country and not specs_made:
                    continue
                quants = self.env['stock.quant'].sudo().search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.location_dest_id.id),
                    ('lot_id', '=', line.lot_id.id if line.lot_id else False),
                ])
                if not quants:
                    continue
                update_vals = {}
                if made_country:
                    update_vals['made_country'] = made_country.id
                if specs_made:
                    update_vals['specs_made'] = specs_made.id
                quants.sudo().write(update_vals)
        return res

    def action_open_upload_csv_wizard(self):
        self.ensure_one()
        return {
            "name": _("Import Serials/Lots from CSV"),
            "type": "ir.actions.act_window",
            "res_model": "stock.move.upload.csv.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_move_id": self.id},
        }

    def _find_country(self, country_str):
        """Lookup res.country by code, exact name, alias, partial name, or ID."""
        if not country_str:
            return self.env['res.country']
        country_str = str(country_str).strip()
        if not country_str:
            return self.env['res.country']

        country_clean = country_str.lower()

        # Known common country code aliases
        COUNTRY_ALIASES = {
            'china': 'CN',
            'cn': 'CN',
            'chn': 'CN',
            'prc': 'CN',
            'p.r.c.': 'CN',
            'people\'s republic of china': 'CN',
            'peoples republic of china': 'CN',
            'mainland china': 'CN',
            'india': 'IN',
            'in': 'IN',
            'ind': 'IN',
            'switzerland': 'CH',
            'ch': 'CH',
            'che': 'CH',
            'swiss': 'CH',
            'united states': 'US',
            'united states of america': 'US',
            'usa': 'US',
            'us': 'US',
            'united kingdom': 'GB',
            'uk': 'GB',
            'gb': 'GB',
            'great britain': 'GB',
            'united arab emirates': 'AE',
            'uae': 'AE',
            'ae': 'AE',
            'vietnam': 'VN',
            'viet nam': 'VN',
            'vn': 'VN',
            'vnm': 'VN',
            'taiwan': 'TW',
            'tw': 'TW',
            'twn': 'TW',
            'hong kong': 'HK',
            'hk': 'HK',
            'hkg': 'HK',
            'singapore': 'SG',
            'sg': 'SG',
            'sgp': 'SG',
            'japan': 'JP',
            'jp': 'JP',
            'jpn': 'JP',
            'korea': 'KR',
            'south korea': 'KR',
            'kr': 'KR',
            'kor': 'KR',
            'germany': 'DE',
            'de': 'DE',
            'deu': 'DE',
        }

        # 1. Alias lookup
        if country_clean in COUNTRY_ALIASES:
            code = COUNTRY_ALIASES[country_clean]
            country = self.env['res.country'].search([('code', '=ilike', code)], limit=1)
            if country:
                return country

        # 2. Exact code match if 2 characters (e.g. IN, US, CN, CH, AE)
        if len(country_str) == 2:
            country = self.env['res.country'].search([('code', '=ilike', country_str)], limit=1)
            if country:
                return country

        # 3. Exact name match (case-insensitive)
        country = self.env['res.country'].search([('name', '=ilike', country_str)], limit=1)
        if country:
            return country

        # 4. Partial name match
        country = self.env['res.country'].search([('name', 'ilike', country_str)], limit=1)
        if country:
            return country

        # 5. Integer ID match
        if country_str.isdigit():
            country = self.env['res.country'].browse(int(country_str))
            if country.exists():
                return country

        return self.env['res.country']

    def action_download_sample_xlsx(self):
        self.ensure_one()
        if openpyxl is None:
            raise UserError(_("Excel export requires the 'openpyxl' library."))

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Serials"

        product = self.product_id
        is_mobile = product.is_mobile_category_selected
        is_dual = product.is_dual_sim if is_mobile else False

        sample_country_name = (
            self.made_in_country_id.name
            or self.made_country.name
            or (self.picking_id and self.picking_id.made_country.name)
            or "India"
        )
        sample_country_name2 = "China"

        if is_mobile and is_dual:
            headers = ["Serials/Lots", "IMEI 1", "IMEI 2", "Made In"]
            rows = [
                ["SER100001", "864201040000001", "864201040000002", sample_country_name],
                ["SER100002", "864201040000003", "864201040000004", sample_country_name2],
            ]
        elif is_mobile:
            headers = ["Serials/Lots", "IMEI 1", "Made In"]
            rows = [
                ["SER100001", "864201040000001", sample_country_name],
                ["SER100002", "864201040000002", sample_country_name2],
            ]
        else:
            headers = ["Serials/Lots", "Made In"]
            rows = [
                ["SER100001", sample_country_name],
                ["SER100002", sample_country_name2],
            ]

        ws.append(headers)
        for r in rows:
            ws.append(r)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        xlsx_data = output.read()

        product_code = self.product_id.default_code or self.product_id.name or 'serials'
        clean_code = "".join(c if c.isalnum() else "_" for c in product_code)
        filename = f"sample_import_{clean_code}.xlsx"

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(xlsx_data),
            'res_model': 'stock.move',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_download_sample_xml(self):
        """Alias for sample template download."""
        return self.action_download_sample_xlsx()

    def action_apply_csv_serial_lines(self, csv_rows, keep_lines=False):
        """Create or update move lines from CSV rows (server-side). Each row: {lot_name, imei, imei2, made_in}."""
        self.ensure_one()
        if not self.product_id:
            raise UserError(_("No product found to generate Serials/Lots for."))
        if not self.location_dest_id:
            raise UserError(_("The stock move has no Destination Location set. Please set the Destination Location before importing serials."))
        context = {
            "default_product_id": self.product_id.id,
            "default_location_dest_id": self.location_dest_id.id,
            "default_location_id": self.location_id.id,
            "default_tracking": self.has_tracking,
            "default_quantity": self.product_qty,
        }
        if self.picking_type_id:
            context["default_picking_type_id"] = self.picking_type_id.id
        if self.company_id:
            context["default_company_id"] = self.company_id.id
        vals_list = self._get_csv_move_line_vals_raw(context, csv_rows)
        if not keep_lines:
            self.move_line_ids.unlink()
        MoveLine = self.env["stock.move.line"]
        for vals in vals_list:
            vals["move_id"] = self.id
            MoveLine.create(vals)

    def _get_csv_move_line_vals_raw(self, context, csv_rows):
        """Return list of move line vals (raw ids) from context and csv_rows. No webclient formatting."""
        default_vals = {}
        for key, value in context.items():
            if key.startswith("default_"):
                default_vals[key[8:]] = value  # remove 'default_'
        vals_list = []
        for row in csv_rows:
            lot_name = (row.get("lot_name") or row.get("serial") or "").strip()
            if not lot_name:
                continue
            imei = (row.get("imei") or row.get("imei1") or "").strip() or False
            imei2 = (row.get("imei2") or "").strip() or False
            made_in_str = (row.get("made_in") or row.get("made_in_country") or row.get("made_country") or row.get("country") or "").strip()

            country = self._find_country(made_in_str) if made_in_str else (
                self.made_in_country_id or self.made_country or (self.picking_id and self.picking_id.made_country)
            )

            original_loc_dest_id = default_vals["location_dest_id"]
            loc_dest = self.env["stock.location"].browse(original_loc_dest_id)
            product = self.env["product.product"].browse(default_vals["product_id"])
            putaway_loc = loc_dest._get_putaway_strategy(product, 1)
            # Fall back to original location if putaway returns empty/invalid record
            resolved_loc_dest_id = putaway_loc.id if putaway_loc and putaway_loc.id else original_loc_dest_id
            line_vals = {
                **default_vals,
                "lot_name": lot_name,
                "quantity": 1,
                "location_dest_id": resolved_loc_dest_id,
                "product_uom_id": product.uom_id.id,
                "imei": imei,
                "imei2": imei2,
            }
            if country:
                line_vals["made_in_country_id"] = country.id
                line_vals["made_country"] = country.id

            vals_list.append(line_vals)
        if default_vals.get("picking_type_id"):
            picking_type = self.env["stock.picking.type"].browse(default_vals["picking_type_id"])
            if picking_type.use_existing_lots:
                self._create_lot_ids_from_move_line_vals(
                    vals_list, default_vals["product_id"], default_vals["company_id"]
                )
        allowed = set(self.env["stock.move.line"]._fields.keys())
        return [{k: v for k, v in v.items() if k in allowed} for v in vals_list]

    @api.model
    def action_generate_lot_line_vals_from_csv(self, context, csv_rows):
        """Generate move line values from CSV rows. Each row is {lot_name, imei, imei2, made_in}.
        Returns same structure as action_generate_lot_line_vals for use in the receipt serial/lot wizard.
        """
        if not context.get('default_product_id'):
            raise UserError(_("No product found to generate Serials/Lots for."))
        default_vals = {}

        def remove_prefix(text, prefix):
            if text.startswith(prefix):
                return text[len(prefix):]
            return text
        for key in context:
            if key.startswith('default_'):
                default_vals[remove_prefix(key, 'default_')] = context[key]

        move = self.browse(context.get('default_move_id')) if context.get('default_move_id') else self.env['stock.move']

        vals_list = []
        for row in csv_rows:
            lot_name = (row.get('lot_name') or row.get('serial') or '').strip()
            if not lot_name:
                continue
            imei = (row.get('imei') or row.get('imei1') or '').strip()
            imei2 = (row.get('imei2') or '').strip()
            made_in_str = (row.get("made_in") or row.get("made_in_country") or row.get("made_country") or row.get("country") or "").strip()

            country = move._find_country(made_in_str) if (made_in_str and move) else (
                self._find_country(made_in_str) if made_in_str else (
                    move.made_in_country_id or move.made_country or (move.picking_id and move.picking_id.made_country) if move else False
                )
            )

            original_loc_dest_id = default_vals['location_dest_id']
            loc_dest = self.env['stock.location'].browse(original_loc_dest_id)
            product = self.env['product.product'].browse(default_vals['product_id'])
            putaway_loc = loc_dest._get_putaway_strategy(product, 1)
            resolved_loc_dest_id = putaway_loc.id if putaway_loc and putaway_loc.id else original_loc_dest_id
            line_vals = {
                **default_vals,
                'lot_name': lot_name,
                'quantity': 1,
                'location_dest_id': resolved_loc_dest_id,
                'product_uom_id': product.uom_id.id,
                'imei': imei or False,
                'imei2': imei2 or False,
            }
            if country:
                line_vals['made_in_country_id'] = country.id
                line_vals['made_country'] = country.id

            vals_list.append(line_vals)
        if default_vals.get('picking_type_id'):
            picking_type = self.env['stock.picking.type'].browse(default_vals['picking_type_id'])
            if picking_type.use_existing_lots:
                self._create_lot_ids_from_move_line_vals(
                    vals_list, default_vals['product_id'], default_vals['company_id']
                )
        for values in vals_list:
            for key, value in list(values.items()):
                if key in self.env['stock.move.line']._fields and value and isinstance(value, int):
                    f = self.env['stock.move.line']._fields[key]
                    if f.type == 'many2one':
                        values[key] = {
                            'id': value,
                            'display_name': self.env[f.comodel_name].browse(value).display_name
                        }
        return vals_list

    def write(self, vals):
        res = super().write(vals)
        # After saving the move, validate all move lines that have IMEI or lot data
        if 'move_line_ids' in vals or 'move_line_nosuggest_ids' in vals:
            for move in self:
                for line in move.move_line_ids.filtered(
                    lambda l: l.imei or l.imei2 or l.lot_name
                ):
                    line._validate_imei_lot_on_save({
                        'imei': line.imei,
                        'imei2': line.imei2,
                        'lot_name': line.lot_name,
                    })
        return res


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    imei = fields.Char(string="IMEI 1", compute="_compute_imei", store=True, readonly=False)
    imei2 = fields.Char(string='IMEI 2', compute="_compute_imei", store=True, readonly=False)

    made_in_country_id = fields.Many2one(
        'res.country',
        string='Made In',
        help='Country of origin for this specific lot/serial. Auto-filled from the quant when a lot is selected.',
    )

    specs_made = fields.Many2one(
        'res.country',
        string='Spec Made For',
        help='Specification made for a specific country.',
        tracking=True
    )

    made_country = fields.Many2one(
        'res.country',
        string='Made In',
        help='Country where the product is manufactured',
        tracking=True
    )

    @api.depends('lot_id')
    def _compute_imei(self):
        for line in self:
            # Incoming lines are filled in manually at receipt time; don't touch them here.
            if not line.lot_id or (line.move_id.picking_id and line.move_id.picking_id.picking_type_id.code == 'incoming'):
                continue
            quant = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.location_id.id),
                ('lot_id', '=', line.lot_id.id),
            ], limit=1)
            if quant:
                line.imei = quant.imei
                line.imei2 = quant.imei2

    def write(self, vals):
        """Override to propagate country fields to quants and validate quant matches"""
        # Validate that quant matches country fields if quant_id is being set
        if 'quant_id' in vals and vals['quant_id']:
            for line in self:
                quant = self.env['stock.quant'].browse(vals['quant_id'])
                # Use country from vals first (so same-write update of quant + country passes), then line/move
                specs_made = vals.get('specs_made') and self.env['res.country'].browse(vals['specs_made'])
                if not specs_made:
                    specs_made = line.specs_made or (line.move_id and line.move_id.specs_made)
                made_country = vals.get('made_country') and self.env['res.country'].browse(vals['made_country'])
                if not made_country:
                    made_country = line.made_country or (line.move_id and line.move_id.made_country)
                # Compare ids for consistency
                specs_made_id = specs_made.id if specs_made else None
                made_country_id = made_country.id if made_country else None

                # if specs_made_id and quant.specs_made and quant.specs_made.id != specs_made_id:
                #     raise ValidationError(_('The selected quant has a different "Spec Made For" (%s) than required (%s).') %
                #                         (quant.specs_made.name, specs_made.name))
                # if made_country_id and quant.made_country and quant.made_country.id != made_country_id:
                #     raise ValidationError(_('The selected quant has a different "Made In" (%s) than required (%s).') %
                #                         (quant.made_country.name, made_country.name))
        
        res = super().write(vals)

        # When made_in_country_id is directly set on a move line, propagate up to picking header.
        if 'made_in_country_id' in vals and vals['made_in_country_id']:
            for line in self:
                if line.move_id:
                    line.move_id.with_context(skip_line_cascade=True).write(
                        {'made_in_country_id': vals['made_in_country_id']}
                    )
                    picking = line.move_id.picking_id
                    if picking and not picking.made_country:
                        picking.sudo().write({'made_country': vals['made_in_country_id']})

        # When lot_id is assigned (by Odoo's reservation engine or manually), auto-fill
        # made_in_country_id / made_country / specs_made on outgoing delivery lines from the matching quant.
        if 'lot_id' in vals and vals['lot_id']:
            for line in self:
                if (not line.made_in_country_id
                        and line.move_id
                        and line.move_id.picking_id.picking_type_id.code == 'outgoing'):
                    quant = self.env['stock.quant'].search([
                        ('product_id', '=', line.product_id.id),
                        ('lot_id', '=', line.lot_id.id),
                        ('location_id', '=', line.location_id.id),
                        ('made_country', '!=', False),
                    ], limit=1)
                    if not quant:
                        quant = self.env['stock.quant'].search([
                            ('product_id', '=', line.product_id.id),
                            ('lot_id', '=', line.lot_id.id),
                            ('made_country', '!=', False),
                        ], limit=1)
                    if quant and quant.specs_made and not line.specs_made:
                        line.specs_made = quant.specs_made.id
                    if quant and quant.made_country:
                        line.made_country = quant.made_country.id
                        line.made_in_country_id = quant.made_country.id
                        if line.move_id:
                            line.move_id.made_in_country_id = quant.made_country.id
                            picking = line.move_id.picking_id
                            if picking and not picking.made_country:
                                picking.sudo().write({'made_country': quant.made_country.id})

        # When move line is done, update related quants with country fields
        if 'state' in vals and vals['state'] == 'done':
            for line in self:
                if line.specs_made or line.made_country:
                    # Find quants created from this move line
                    quants = self.env['stock.quant'].search([
                        ('product_id', '=', line.product_id.id),
                        ('location_id', '=', line.location_dest_id.id),
                        ('lot_id', '=', line.lot_id.id if line.lot_id else False),
                    ])
                    if quants:
                        update_vals = {}
                        if line.specs_made:
                            update_vals['specs_made'] = line.specs_made.id
                        if line.made_country:
                            update_vals['made_country'] = line.made_country.id
                        if update_vals:
                            quants.write(update_vals)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # Validate quants match country fields before creating
        for vals in vals_list:
            if vals.get('quant_id'):
                quant = self.env['stock.quant'].browse(vals['quant_id'])
                # Get country fields from move if available
                move_id = vals.get('move_id')
                specs_made = None
                made_country = None
                if move_id:
                    move = self.env['stock.move'].browse(move_id)
                    specs_made = move.specs_made
                    made_country = move.made_country
                
                # Also check if set directly in vals
                if vals.get('specs_made'):
                    specs_made = self.env['res.country'].browse(vals['specs_made'])
                if vals.get('made_country'):
                    made_country = self.env['res.country'].browse(vals['made_country'])
                
                # Validate quant matches
                # if specs_made and quant.specs_made and quant.specs_made.id != specs_made.id:
                #     raise ValidationError(_('The selected quant has a different "Spec Made For" (%s) than required (%s).') %
                #                         (quant.specs_made.name, specs_made.name))
                # if made_country and quant.made_country and quant.made_country.id != made_country.id:
                #     raise ValidationError(_('The selected quant has a different "Made In" (%s) than required (%s).') %
                #                         (quant.made_country.name, made_country.name))
        
        move_lines = super().create(vals_list)
        for line in move_lines:
            # Propagate country fields from move to move line if not already set
            if line.move_id:
                if not line.specs_made and line.move_id.specs_made:
                    line.specs_made = line.move_id.specs_made.id
                if not line.made_country and line.move_id.made_country:
                    line.made_country = line.move_id.made_country.id
                if not line.made_in_country_id and line.made_country:
                    line.made_in_country_id = line.made_country.id
                elif not line.made_country and line.made_in_country_id:
                    line.made_country = line.made_in_country_id.id
                elif not line.made_in_country_id and line.move_id.made_in_country_id:
                    line.made_in_country_id = line.move_id.made_in_country_id.id
                # Populate made_in_country_id / made_country / specs_made for delivery lines from the quant
                if (not line.made_in_country_id
                        and line.lot_id
                        and line.move_id.picking_id.picking_type_id.code == 'outgoing'):
                    quant = self.env['stock.quant'].search([
                        ('product_id', '=', line.product_id.id),
                        ('lot_id', '=', line.lot_id.id),
                        ('made_country', '!=', False),
                    ], limit=1)
                    if quant and quant.specs_made and not line.specs_made:
                        line.specs_made = quant.specs_made.id
                    if quant and quant.made_country:
                        line.made_country = quant.made_country.id
                        line.made_in_country_id = quant.made_country.id
                        if line.move_id:
                            line.move_id.made_in_country_id = quant.made_country.id
                            picking = line.move_id.picking_id
                            if picking and not picking.made_country:
                                picking.sudo().write({'made_country': quant.made_country.id})
            if line.move_id and not line.imei:
                # 1️. First try: get IMEI from related incoming PO move lines
                related_moves = self.env['stock.move.line'].search([
                    ('product_id', '=', line.product_id.id),
                    ('lot_id', '=', line.lot_id.id),
                    ('location_dest_id.usage', '=', 'internal'),
                    ('location_id.usage', '=', 'supplier'),
                ], limit=1)

                if related_moves:
                    line.imei = related_moves.imei
                    line.imei2 = related_moves.imei2
                else:
                    # 2️. Fallback: try to get from stock.quant (Inventory Adjustments)
                    quant = self.env['stock.quant'].search([
                        ('product_id', '=', line.product_id.id),
                        ('lot_id', '=', line.lot_id.id),
                        ('location_id', '=', line.location_id.id),
                    ], limit=1)

                    if quant:
                        line.imei = quant.imei
                        line.imei2 = quant.imei2

        return move_lines

    def _validate_imei_lot_on_save(self, vals):
        """Called from create/write to block saving invalid IMEI or duplicate serial/lot."""
        record = self[:1] if self else self.browse()
        imei = vals.get('imei') if 'imei' in vals else (record.imei or None)
        imei2 = vals.get('imei2') if 'imei2' in vals else (record.imei2 or None)
        lot_name = vals.get('lot_name') if 'lot_name' in vals else (record.lot_name or None)

        # Fetch current product ID
        product_id = vals.get('product_id') if isinstance(vals.get('product_id'), int) else (
            record.product_id.id if record else False)

        picking_type_code = None
        if record and record.move_id and record.move_id.picking_id:
            picking_type_code = record.move_id.picking_id.picking_type_id.code
        elif vals.get('move_id'):
            move = self.env['stock.move'].browse(vals['move_id'])
            if move.picking_id:
                picking_type_code = move.picking_id.picking_type_id.code
        is_outgoing = picking_type_code == 'outgoing'

        # Validate IMEI 1
        if imei:
            if not imei.isdigit() or len(imei) != 15:
                raise ValidationError(_('IMEI 1 must be a 15-digit number. Got: %s') % imei)

            # Check stock existence and product mismatch
            quant = self.env['stock.quant'].search([
                '|', ('imei', '=', imei), ('imei2', '=', imei)
            ])

            if is_outgoing:
                if not quant:
                    raise ValidationError(_('IMEI 1 (%s) does not exist in stock.') % imei)
                if product_id and any(q.product_id.id != product_id for q in quant):
                    matched_product = quant[0].product_id.display_name
                    raise ValidationError(
                        _('IMEI 1 (%s) is not valid for this product. It belongs to: %s.') % (imei, matched_product))
            else:
                # Incoming/Internal duplicate checks
                exist = self.search([('imei', '=', imei), ('id', 'not in', self.ids)], limit=1)
                if exist:
                    raise ValidationError(_('IMEI 1 (%s) is already used in another stock line.') % imei)
                if len(quant) > 1:
                    raise ValidationError(_('IMEI 1 (%s) is already allocated in stock.') % imei)

        # Validate IMEI 2
        if imei2:
            if not imei2.isdigit() or len(imei2) != 15:
                raise ValidationError(_('IMEI 2 must be a 15-digit number. Got: %s') % imei2)

            # Check stock existence and product mismatch
            quant = self.env['stock.quant'].search([
                '|', ('imei', '=', imei2), ('imei2', '=', imei2)
            ])

            if is_outgoing:
                if not quant:
                    raise ValidationError(_('IMEI 2 (%s) does not exist in stock.') % imei2)
                if product_id and any(q.product_id.id != product_id for q in quant):
                    matched_product = quant[0].product_id.display_name
                    raise ValidationError(
                        _('IMEI 2 (%s) is not valid for this product. It belongs to: %s.') % (imei2, matched_product))
            else:
                # Incoming/Internal duplicate checks
                exist = self.search([('imei2', '=', imei2), ('id', 'not in', self.ids)], limit=1)
                if exist:
                    raise ValidationError(_('IMEI 2 (%s) is already used in another stock line.') % imei2)
                if len(quant) > 1:
                    raise ValidationError(_('IMEI 2 (%s) is already allocated in stock.') % imei2)

        # IMEI 1 and IMEI 2 must differ (except Samsung/OnePlus)
        if imei and imei2 and imei == imei2:
            product = self.env['product.product'].browse(product_id) if product_id else self.env['product.product']
            brand_name = (product.product_tmpl_id.brand_id.name or '').lower() if product else ''
            if brand_name not in ('samsung', 'oneplus'):
                raise ValidationError(_('IMEI 1 and IMEI 2 must be different.'))

        # Validate Serial/Lot number
        if lot_name:
            exist = self.search([('lot_name', '=', lot_name), ('id', 'not in', self.ids)], limit=1)
            if exist:
                raise ValidationError(_('Serial number (%s) is already used in another line.') % lot_name)
            quant = self.env['stock.quant'].search([('lot_id.name', '=', lot_name)])
            if len(quant) > 0:
                raise ValidationError(_('Serial number (%s) is already registered in stock.') % lot_name)

    def create(self, vals_list):
        records_vals = [vals_list] if isinstance(vals_list, dict) else vals_list
        for vals in records_vals:
            self._validate_imei_lot_on_save(vals)
        return super().create(vals_list)

    def write(self, vals):
        if any(f in vals for f in ('imei', 'imei2', 'lot_name')):
            for record in self:
                record._validate_imei_lot_on_save(vals)
        return super().write(vals)

    def validate_imei_and_serial_number(self):
        # some time it shows None
        # if self._context.get('active_model') != 'purchase.order':
        #     return 

        # 1. Validate IMEI number and Serial number
        for record in self:

            # 1. Ensure IMEIs are not empty
            if record.move_id.show_IMEI_field2:
                if not record.imei or not record.imei2:
                    raise ValidationError(_('Please enter both IMEI numbers.'))
            elif record.move_id.show_IMEI_field:
                if not record.imei:
                    raise ValidationError(_('Please enter IMEI number.'))

            # 2. Validate IMEI format (15 digit number)
            if record.move_id.show_IMEI_field2:
                if not record.imei.isdigit() or len(record.imei) != 15 or not record.imei2.isdigit() or len(
                        record.imei2) != 15:
                    raise ValidationError(_('IMEI number must be a 15-digit number.'))
            elif record.move_id.show_IMEI_field:
                if not record.imei.isdigit() or len(record.imei) != 15:
                    raise ValidationError(_('IMEI number must be a 15-digit number.'))

            # 3.1 Uniqueness of IMEI check in same lines
            if record.move_id.show_IMEI_field2:
                exist = self.search([('imei', '=', record.imei), ('id', '!=', record.id)], limit=1)
                if exist:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))
                exist = self.search([('imei2', '=', record.imei2), ('id', '!=', record.id)], limit=1)
                if exist:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei2))
                exist = self.search([('imei', '=', record.imei2), ('id', '!=', record.id)], limit=1)
                if exist:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei2))
                exist = self.search([('imei2', '=', record.imei), ('id', '!=', record.id)], limit=1)
                if exist:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei1))
            elif record.move_id.show_IMEI_field:
                exist = self.search([('imei', '=', record.imei), ('id', '!=', record.id)], limit=1)
                if exist:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))

            # 3.2 Uniqueness of IMEI check in all other saved items
            if record.move_id.show_IMEI_field2:

                # check if brand is samsung or oneplus, as these two brands have imei1 and imei2 field's same value 
                brand_record = record.sudo().product_id.product_tmpl_id.brand_id
                brand_name = brand_record.name if brand_record else ''
                is_brand_samsung_or_oneplus = False
                if brand_name and (brand_name.lower() == 'samsung' or brand_name.lower() == 'oneplus'):
                    is_brand_samsung_or_oneplus = True

                if not is_brand_samsung_or_oneplus:
                    if record.imei == record.imei2:
                        raise ValidationError(
                            f"Both IMEI numbers must be different for product '{record.sudo().product_id.product_tmpl_id.name}'")

                imei_results = self.env['stock.quant'].search([
                    '|',
                    ('imei', '=', record.imei),
                    ('imei2', '=', record.imei)
                ])
                imei2_results = self.env['stock.quant'].search([
                    '|',
                    ('imei', '=', record.imei2),
                    ('imei2', '=', record.imei2)
                ])

                if len(imei_results) > 1:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))
                if len(imei2_results) > 1:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei2))

            elif record.move_id.show_IMEI_field:
                result_items = self.env['stock.quant'].search([
                    '|',
                    ('imei', '=', record.imei),
                    ('imei2', '=', record.imei)
                ])

                if len(result_items) > 1:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))

            # 4.1 Uniqueness of Serial number check in same lines
            exist = self.search([('lot_name', '=', record.lot_name), ('id', '!=', record.id)], limit=1)
            if exist:
                raise ValidationError(
                    _('Serial number must be unique, the serial number(%s) is already used in another stock item.' % record.lot_name))

            # 4.2 Uniqueness of Serial number check in all other saved items
            results = self.env['stock.quant'].search([
                ('lot_id.name', '=', record.lot_name)
            ])

            if len(results) > 0:
                raise ValidationError(
                    _('Serial number must be unique, the Serial number(%s) is already used in another stock item.' % record.lot_name))

    @api.constrains('imei', 'imei2')
    def _constrains_validate_imei(self):
        for record in self:
            if not record.move_id:
                continue

            picking_type_code = (
                record.move_id.picking_id.picking_type_id.code
                if record.move_id.picking_id else None
            )
            is_outgoing = picking_type_code == 'outgoing'

            if record.move_id.show_IMEI_field2:
                if record.imei and (not record.imei.isdigit() or len(record.imei) != 15):
                    raise ValidationError(_('IMEI 1 must be a 15-digit number.'))
                if record.imei2 and (not record.imei2.isdigit() or len(record.imei2) != 15):
                    raise ValidationError(_('IMEI 2 must be a 15-digit number.'))
                if record.imei and record.imei2 and record.imei == record.imei2:
                    brand_name = (record.product_id.product_tmpl_id.brand_id.name or '').lower()
                    if brand_name not in ('samsung', 'oneplus'):
                        raise ValidationError(_('IMEI 1 and IMEI 2 must be different.'))
                if not is_outgoing:
                    if record.imei:
                        exist = self.search([('imei', '=', record.imei), ('id', '!=', record.id)], limit=1)
                        if exist:
                            raise ValidationError(_('IMEI 1 (%s) is already used in another stock item.') % record.imei)
                        quant = self.env['stock.quant'].search([
                            '|', ('imei', '=', record.imei), ('imei2', '=', record.imei)
                        ])
                        if len(quant) > 1:
                            raise ValidationError(_('IMEI 1 (%s) is already used in stock.') % record.imei)
                    if record.imei2:
                        exist = self.search([('imei2', '=', record.imei2), ('id', '!=', record.id)], limit=1)
                        if exist:
                            raise ValidationError(_('IMEI 2 (%s) is already used in another stock item.') % record.imei2)
                        quant = self.env['stock.quant'].search([
                            '|', ('imei', '=', record.imei2), ('imei2', '=', record.imei2)
                        ])
                        if len(quant) > 1:
                            raise ValidationError(_('IMEI 2 (%s) is already used in stock.') % record.imei2)

            elif record.move_id.show_IMEI_field:
                if record.imei and (not record.imei.isdigit() or len(record.imei) != 15):
                    raise ValidationError(_('IMEI must be a 15-digit number.'))
                if not is_outgoing and record.imei:
                    exist = self.search([('imei', '=', record.imei), ('id', '!=', record.id)], limit=1)
                    if exist:
                        raise ValidationError(_('IMEI (%s) is already used in another stock item.') % record.imei)
                    quant = self.env['stock.quant'].search([
                        '|', ('imei', '=', record.imei), ('imei2', '=', record.imei)
                    ])
                    if len(quant) > 1:
                        raise ValidationError(_('IMEI (%s) is already used in stock.') % record.imei)

    @api.constrains('lot_name')
    def _constrains_validate_lot_name(self):
        for record in self:
            if not record.lot_name:
                continue
            exist = self.search([('lot_name', '=', record.lot_name), ('id', '!=', record.id)], limit=1)
            if exist:
                raise ValidationError(
                    _('Serial number (%s) is already used in another line.') % record.lot_name)
            quant = self.env['stock.quant'].search([('lot_id.name', '=', record.lot_name)])
            if len(quant) > 0:
                raise ValidationError(
                    _('Serial number (%s) is already used in another stock item.') % record.lot_name)

    @api.onchange('imei', 'imei2')
    def _onchange_validate_imei(self):
        warning_msgs = []

        picking_type_code = (
            self.move_id.picking_id.picking_type_id.code
            if self.move_id and self.move_id.picking_id else None
        )
        is_outgoing = picking_type_code == 'outgoing'

        # IMEI 1 validations
        if self.imei:
            if not self.imei.isdigit() or len(self.imei) != 15:
                warning_msgs.append(_('IMEI 1 must be a 15-digit number.'))
            elif not is_outgoing:
                exist = self.search([('imei', '=', self.imei), ('id', '!=', self._origin.id)], limit=1)
                if exist:
                    warning_msgs.append(_('IMEI 1 (%s) is already used in another stock item.') % self.imei)
                quant_exist = self.env['stock.quant'].search([
                    '|', ('imei', '=', self.imei), ('imei2', '=', self.imei)
                ])
                if len(quant_exist) > 1:
                    warning_msgs.append(_('IMEI 1 (%s) is already used in stock.') % self.imei)

        # IMEI 2 validations
        if self.move_id.show_IMEI_field2 and self.imei2:
            if not self.imei2.isdigit() or len(self.imei2) != 15:
                warning_msgs.append(_('IMEI 2 must be a 15-digit number.'))
            elif not is_outgoing:
                exist = self.search([('imei2', '=', self.imei2), ('id', '!=', self._origin.id)], limit=1)
                if exist:
                    warning_msgs.append(_('IMEI 2 (%s) is already used in another stock item.') % self.imei2)
                quant_exist = self.env['stock.quant'].search([
                    '|', ('imei', '=', self.imei2), ('imei2', '=', self.imei2)
                ])
                if len(quant_exist) > 1:
                    warning_msgs.append(_('IMEI 2 (%s) is already used in stock.') % self.imei2)

        # IMEI 1 and IMEI 2 must differ (except Samsung/OnePlus)
        if self.move_id.show_IMEI_field2 and self.imei and self.imei2 and self.imei == self.imei2:
            brand_name = (self.product_id.product_tmpl_id.brand_id.name or '').lower()
            if brand_name not in ('samsung', 'oneplus'):
                warning_msgs.append(_('IMEI 1 and IMEI 2 must be different.'))

        if warning_msgs:
            return {'warning': {'title': _('IMEI Validation'), 'message': '\n'.join(warning_msgs)}}

    @api.onchange('lot_name')
    def _onchange_validate_lot_name(self):
        if not self.lot_name:
            return
        warning_msgs = []

        exist = self.search([('lot_name', '=', self.lot_name), ('id', '!=', self._origin.id)], limit=1)
        if exist:
            warning_msgs.append(_('Serial number (%s) is already used in another line.') % self.lot_name)

        quant_exist = self.env['stock.quant'].search([('lot_id.name', '=', self.lot_name)])
        if len(quant_exist) > 0:
            warning_msgs.append(_('Serial number (%s) is already used in another stock item.') % self.lot_name)

        if warning_msgs:
            return {'warning': {'title': _('Serial Number Validation'), 'message': '\n'.join(warning_msgs)}}

    def _synchronize_quant(self, quantity, location, action="available", in_date=False, **quants_value):
        """Override to stamp made_country / specs_made onto the destination quant
        immediately after the standard quant move.

        _synchronize_quant is called once per move line during _action_done and is
        the earliest reliable point where the destination quant (whether newly
        created or incremented) already exists in the DB.  We only write when
        moving INTO a location (quantity > 0) so we don't pollute source quants.
        """
        result = super()._synchronize_quant(quantity, location, action=action, in_date=in_date, **quants_value)

        # Only propagate when we are adding stock to the destination (incoming direction)
        if quantity > 0:
            # Resolution order: line → move.made_country → move.made_in_country_id → picking header
            # made_in_country_id comes from ks_templates stock.move and carries
            # country-of-origin data propagated from PO/SO lines.
            made_country = (
                self.made_country
                or (self.move_id and self.move_id.made_country)
                or (self.move_id and self.move_id.made_in_country_id)
                or (self.move_id and self.move_id.picking_id and self.move_id.picking_id.made_country)
            )
            specs_made = (
                self.specs_made
                or (self.move_id and self.move_id.specs_made)
                or (self.move_id and self.move_id.picking_id and self.move_id.picking_id.specs_made)
            )
            if made_country or specs_made:
                lot = quants_value.get('lot', self.lot_id)
                quants = self.env['stock.quant'].sudo().search([
                    ('product_id', '=', self.product_id.id),
                    ('location_id', '=', location.id),
                    ('lot_id', '=', lot.id if lot else False),
                ])
                if quants:
                    update_vals = {}
                    if made_country:
                        update_vals['made_country'] = made_country.id
                    if specs_made:
                        update_vals['specs_made'] = specs_made.id
                    quants.sudo().write(update_vals)

        return result

    @api.onchange('quant_id')
    def _onchange_quant_id_get_imei(self):
        for line in self:
            if line.quant_id.imei:
                line.imei = line.quant_id.imei
            if line.quant_id.imei2:
                line.imei2 = line.quant_id.imei2
            # Propagate country fields from quant
            if line.quant_id.specs_made:
                line.specs_made = line.quant_id.specs_made.id
            if line.quant_id.made_country:
                line.made_country = line.quant_id.made_country.id
                line.made_in_country_id = line.quant_id.made_country.id
                if line.move_id:
                    line.move_id.made_in_country_id = line.quant_id.made_country.id

    @api.onchange('lot_id')
    def _onchange_lot_id_fill_made_in_country(self):
        """When a Lot/Serial Number is selected on a delivery line, auto-fill
        made_in_country_id / made_country / specs_made from the matching stock.quant
        so the country of origin and spec are immediately visible on the same row."""
        for line in self:
            if not line.lot_id:
                continue
            quant = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('lot_id', '=', line.lot_id.id),
                ('location_id', '=', line.location_id.id),
                ('made_country', '!=', False),
            ], limit=1)
            if not quant:
                # Fallback: search without location restriction
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('lot_id', '=', line.lot_id.id),
                    ('made_country', '!=', False),
                ], limit=1)
            if quant and quant.specs_made and not line.specs_made:
                line.specs_made = quant.specs_made.id
            if quant and quant.made_country:
                line.made_country = quant.made_country.id
                line.made_in_country_id = quant.made_country.id
                if line.move_id:
                    line.move_id.made_in_country_id = quant.made_country.id


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    specs_made = fields.Many2one(
        'res.country',
        string='Spec Made For',
        help='Specification made for a specific country.',
        tracking=True
    )

    made_country = fields.Many2one(
        'res.country',
        string='Made In',
        tracking=True,
        help='Country where the product is manufactured',
    )

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        for picking in pickings:
            if picking.specs_made and picking.made_country and picking.picking_type_id.code == 'outgoing':
                picking._update_move_quantities_by_country_stock()
        return pickings

    def write(self, vals):
        # Prevent changing Spec Made For / Made In once delivery is done (validated)
        if 'specs_made' in vals or 'made_country' in vals:
            if not self.env.context.get('skip_country_validation'):
                done = self.filtered(
                    lambda p: p.state == 'done' and p.picking_type_id.code == 'incoming'
                )
                if done:
                    raise ValidationError(_('You cannot change "Spec Made For" or "Made In" after the receipt has been validated.'))
        res = super().write(vals)
        if 'specs_made' in vals or 'made_country' in vals:
            for picking in self:
                if picking.picking_type_id.code == 'incoming':
                    picking._propagate_country_fields_to_moves()
        return res

    def action_confirm(self):
        """Override to propagate specs_made and made_country to moves and move lines"""
        res = super().action_confirm()
        self._propagate_country_fields_to_moves()
        return res

    def action_assign(self):
        """After reserving stock (assigning lots), sync made_in_country_id from move lines
        up to picking.made_country for outgoing deliveries."""
        res = super().action_assign()
        self._sync_country_from_lines_to_picking()
        return res

    def _sync_country_from_lines_to_picking(self):
        """For outgoing pickings: read made_in_country_id from reserved move lines
        (populated from quants) and set it on the picking header made_country."""
        for picking in self:
            if picking.picking_type_id.code != 'outgoing':
                continue
            country = None
            for move in picking.move_ids:
                for line in move.move_line_ids:
                    if line.made_in_country_id:
                        country = line.made_in_country_id
                        break
                if country:
                    break
            if country:
                # bypass write() validation since picking is not done yet
                picking.sudo().with_context(skip_country_validation=True).write(
                    {'made_country': country.id}
                )

    def _propagate_country_fields_to_moves(self):
        """Propagate specs_made and made_country from picking header to moves and move lines.

        Only fills in blanks — never overwrites a value that was already set at the
        move or move-line level.  This preserves per-line countries (e.g. Anguilla on
        a line when the picking header is India).
        """
        for picking in self:
            if not picking.specs_made and not picking.made_country:
                continue

            if picking.picking_type_id.code == 'incoming':
                # Incoming receipts: picking.made_country → move.made_in_country_id (the visible
                # "Made In" column on the Operations tab lines, from ks_templates stock.move).
                # Also fill move.made_country and move_line.made_country for quant propagation.
                for move in picking.move_ids:
                    move_vals = {}
                    if picking.made_country and not move.made_in_country_id:
                        move_vals['made_in_country_id'] = picking.made_country.id
                    if picking.made_country and not move.made_country:
                        move_vals['made_country'] = picking.made_country.id
                    if picking.specs_made and not move.specs_made:
                        move_vals['specs_made'] = picking.specs_made.id
                    if move_vals:
                        move.write(move_vals)
                for line in picking.move_line_ids:
                    line_vals = {}
                    if picking.made_country and not line.made_country:
                        line_vals['made_country'] = picking.made_country.id
                    if picking.specs_made and not line.specs_made:
                        line_vals['specs_made'] = picking.specs_made.id
                    if line_vals:
                        line.write(line_vals)
            else:
                # Outgoing and other types: fill move.made_country / move_line.made_country
                for move in picking.move_ids:
                    move_vals = {}
                    if picking.specs_made and not move.specs_made:
                        move_vals['specs_made'] = picking.specs_made.id
                    if picking.made_country and not move.made_country:
                        move_vals['made_country'] = picking.made_country.id
                    if move_vals:
                        move.write(move_vals)
                for line in picking.move_line_ids:
                    line_vals = {}
                    if picking.specs_made and not line.specs_made:
                        line_vals['specs_made'] = picking.specs_made.id
                    if picking.made_country and not line.made_country:
                        line_vals['made_country'] = picking.made_country.id
                    if line_vals:
                        line.write(line_vals)

    def _update_move_quantities_by_country_stock(self):
        """Update move (product line) quantities to available stock for Spec Made For + Made In.
        When both specs_made and made_country are set, cap each move's product_uom_qty to the
        available quantity in the source location matching those country fields.
        Also assign serial/lot and IMEI on move lines from matching quants.
        """
        for picking in self:
            for move, assign_qty in picking._get_country_stock_assign_quantities():
                if move.product_uom_qty != assign_qty:
                    move.write({'product_uom_qty': assign_qty})
            picking._assign_move_line_quants_by_country_fields(persist=True)

    def _assign_move_line_quants_by_country_fields(self, persist=True):
        """Assign lot/serial and IMEI on move lines from quants matching Spec Made For + Made In.
        Each line gets a distinct matching quant (no reuse). persist=True: write to DB; False: set in memory for onchange.
        First clears any line whose current quant does not match picking's Spec Made For/Made In, so validation passes.
        """
        self.ensure_one()
        if not self.specs_made or not self.made_country:
            return
        specs_made_id = self.specs_made.id
        made_country_id = self.made_country.id

        # First pass: clear quant/lot/IMEI on any line whose current quant doesn't match picking's country (so later write(quant_id=...) won't raise validation)
        for move_line in self.move_line_ids:
            if not move_line.product_id or not move_line.location_id:
                continue
            quant = move_line.quant_id if hasattr(move_line, 'quant_id') and move_line.quant_id else None
            if quant:
                if (quant.specs_made and quant.specs_made.id != specs_made_id) or (quant.made_country and quant.made_country.id != made_country_id):
                    clear_vals = {
                        'lot_id': False,
                        'lot_name': False,
                        'imei': False,
                        'imei2': False,
                        'quant_id': False,
                        'specs_made': specs_made_id,
                        'made_country': made_country_id,
                    }
                    if persist:
                        move_line.write(clear_vals)
                    else:
                        for k, v in clear_vals.items():
                            setattr(move_line, k, v)

        # Second pass: assign matching quants (each line gets a distinct quant)
        assigned_quant_ids = {}
        for move_line in self.move_line_ids:
            if not move_line.product_id or not move_line.location_id:
                continue
            key = (move_line.product_id.id, move_line.location_id.id)
            domain = [
                ('product_id', '=', move_line.product_id.id),
                ('location_id', '=', move_line.location_id.id),
                ('quantity', '>', 0),
                ('specs_made', '=', specs_made_id),
                ('made_country', '=', made_country_id),
            ]
            already_assigned = assigned_quant_ids.setdefault(key, set())
            if already_assigned:
                domain.append(('id', 'not in', list(already_assigned)))
            quant = self.env['stock.quant'].search(domain, limit=1)
            if not quant:
                # No matching quant: clear serial/IMEI so they match the selected location
                clear_vals = {
                    'lot_id': False,
                    'lot_name': False,
                    'imei': False,
                    'imei2': False,
                    'quant_id': False,
                    'specs_made': specs_made_id,
                    'made_country': made_country_id,
                }
                if persist:
                    move_line.write(clear_vals)
                else:
                    for k, v in clear_vals.items():
                        setattr(move_line, k, v)
                continue
            already_assigned.add(quant.id)
            update_vals = {
                'specs_made': specs_made_id,
                'made_country': made_country_id,
            }
            if quant.lot_id:
                update_vals['lot_id'] = quant.lot_id.id
                update_vals['lot_name'] = quant.lot_id.name
            if quant.imei:
                update_vals['imei'] = quant.imei
            if quant.imei2:
                update_vals['imei2'] = quant.imei2
            if quant.id:
                update_vals['quant_id'] = quant.id
            if persist:
                move_line.write(update_vals)
            else:
                for k, v in update_vals.items():
                    setattr(move_line, k, v)

    def _get_country_stock_assign_quantities(self):
        """Return list of (move, assign_qty) for this picking based on Spec Made For + Made In stock.
        assign_qty = min(move.product_uom_qty, available for that product/location).
        """
        self.ensure_one()
        if not self.specs_made or not self.made_country or self.picking_type_id.code != 'outgoing' or not self.move_ids:
            return []

        move_ids = self.move_ids
        product_ids = move_ids.mapped('product_id').ids
        location_ids = move_ids.mapped('location_id').ids
        if not product_ids or not location_ids:
            return []

        quants = self.env['stock.quant'].read_group(
            [
                ('product_id', 'in', product_ids),
                ('location_id', 'in', location_ids),
                ('specs_made', '=', self.specs_made.id),
                ('made_country', '=', self.made_country.id),
                ('quantity', '>', 0),
            ],
            ['product_id', 'location_id', 'quantity:sum'],
            ['product_id', 'location_id'],
            lazy=False,
        )
        available = {}
        for q in quants:
            pid = q.get('product_id')
            lid = q.get('location_id')
            if pid is None or lid is None:
                continue
            pid = pid[0] if isinstance(pid, tuple) else pid
            lid = lid[0] if isinstance(lid, tuple) else lid
            qty = q.get('quantity', 0) or 0
            available[(pid, lid)] = qty

        result = []
        for move in move_ids.sorted(key=lambda m: m.id):
            if not move.product_id or not move.location_id:
                continue
            key = (move.product_id.id, move.location_id.id)
            avail = available.get(key, 0.0)
            if avail <= 0:
                assign_qty = 0.0
            else:
                assign_qty = min(move.product_uom_qty, avail)
            available[key] = avail - assign_qty
            result.append((move, assign_qty))
        return result

    @api.onchange('specs_made', 'made_country')
    def _onchange_specs_made_made_country_update_quantities(self):
        """When Made In / Spec Made For changes on the picking header:
        - Outgoing: update reserved quantities and assign matching quants (existing behaviour).
        - Incoming: bulk-fill picking.made_country → move.made_in_country_id on every
          move line that has no country yet, so the user sets it once for all lines.
        """
        if self.picking_type_id.code == 'outgoing':
            if self.specs_made and self.made_country:
                for move, assign_qty in self._get_country_stock_assign_quantities():
                    move.product_uom_qty = assign_qty
                self._assign_move_line_quants_by_country_fields(persist=False)
        elif self.picking_type_id.code == 'incoming':
            # Bulk-fill in memory — persisted on save via write() → _propagate_country_fields_to_moves()
            for move in self.move_ids:
                if self.made_country and not move.made_in_country_id:
                    move.made_in_country_id = self.made_country
                if self.specs_made and not move.specs_made:
                    move.specs_made = self.specs_made

    def button_validate(self):
        """Override to validate country fields, assign matching quants, and propagate before validation"""
        # For Delivery Orders (OUT) only: require Spec Made For before validation.
        # Receipts (IN) are excluded — made_country is stamped on IN either via
        # PO auto-sync or by the user; specs_made is optional on receipts.
        # for picking in self:
        #     if (picking.picking_type_id.code == 'outgoing'
        #             and picking.state in ('draft', 'waiting', 'confirmed', 'assigned')):
        #         if not picking.specs_made:
        #             raise ValidationError(_('Please set "Spec Made For" field before validating the delivery order.'))
        
        # Assign matching quants based on country fields and validate
        for picking in self:
            picking._assign_quants_by_country_fields()
        
        # Propagate fields to moves and move lines before validation
        self._propagate_country_fields_to_moves()
        
        packaging_category = self.env.ref('ks_product_master.product_category_type_packaging_material',
                                          raise_if_not_found=False)

        for picking in self:
            for line in picking.move_line_ids:
                product = line.sudo().product_id
                category = product.sudo().categ_id
                if line.picking_type_id.code != 'outgoing' and category != packaging_category:  # dont validate if it's outgoing picking (sales order)
                    line.sudo().validate_imei_and_serial_number()

        res = super().button_validate()

        # After validation is fully done, push made_country / specs_made from every
        # move line down to its quant.  This is the definitive propagation step and
        # covers all cases: new quants, existing quants that were only incremented,
        # and non-lot-tracked products that _action_done may have missed.
        for picking in self:
            if picking.state != 'done':
                continue
            for line in picking.move_line_ids:
                made_country = (
                    line.made_country
                    or (line.move_id and line.move_id.made_country)
                    or (line.move_id and line.move_id.made_in_country_id)
                    or picking.made_country
                )
                specs_made = line.specs_made or (line.move_id and line.move_id.specs_made) or picking.specs_made
                if not made_country and not specs_made:
                    continue
                quants = self.env['stock.quant'].sudo().search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.location_dest_id.id),
                    ('lot_id', '=', line.lot_id.id if line.lot_id else False),
                ])
                if not quants:
                    continue
                update_vals = {}
                if made_country:
                    update_vals['made_country'] = made_country.id
                if specs_made:
                    update_vals['specs_made'] = specs_made.id
                quants.sudo().write(update_vals)

        return res

    def _assign_quants_by_country_fields(self):
        """Assign quants to move lines based on specs_made and made_country fields"""
        self.ensure_one()
        
        if not self.specs_made or not self.made_country:
            return
        
        missing_quants = []
        
        for move_line in self.move_line_ids:
            if not move_line.product_id or not move_line.location_id:
                continue
            
            # Build domain to find matching quant - filter by product, specs_made, and made_country
            domain = [
                ('product_id', '=', move_line.product_id.id),
                ('location_id', '=', move_line.location_id.id),
                ('quantity', '>', 0),  # Only available quants
                ('specs_made', '=', self.specs_made.id),
                ('made_country', '=', self.made_country.id),
            ]
            
            # Check if existing serial number matches country fields
            if move_line.lot_id:
                domain_with_lot = domain + [('lot_id', '=', move_line.lot_id.id)]
                quant_with_lot = self.env['stock.quant'].search(domain_with_lot, limit=1)
                
                if not quant_with_lot:
                    # Existing serial doesn't match country fields - clear it
                    move_line.write({
                        'lot_id': False,
                        'lot_name': False,
                        'imei': False,
                        'imei2': False,
                        'quant_id': False,
                    })
            
            # Now find available quant matching country fields (regardless of previous serial)
            quant = self.env['stock.quant'].search(domain, limit=1)
            
            # if not quant:
            #     # No matching quant found
            #     missing_quants.append(
            #         _('Product: %s - No inventory found matching Spec Made For: %s and Made In: %s') %
            #         (move_line.product_id.display_name, self.specs_made.name, self.made_country.name)
            #     )
            #     continue
            
            # If quant found, update move line with new serial number and IMEI
            update_vals = {}
            if quant.lot_id:
                update_vals['lot_id'] = quant.lot_id.id
                update_vals['lot_name'] = quant.lot_id.name
            if quant.imei:
                update_vals['imei'] = quant.imei
            if quant.imei2:
                update_vals['imei2'] = quant.imei2
            if quant.id:
                update_vals['quant_id'] = quant.id
            # Also propagate country fields
            update_vals['specs_made'] = self.specs_made.id
            update_vals['made_country'] = self.made_country.id
            
            if update_vals:
                move_line.write(update_vals)
        
        # Raise validation error if any move lines don't have matching quants
        # if missing_quants:
        #     error_message = _('Cannot validate delivery order. The following products do not have matching inventory:\n\n%s') % '\n'.join(missing_quants)
        #     raise ValidationError(error_message)
