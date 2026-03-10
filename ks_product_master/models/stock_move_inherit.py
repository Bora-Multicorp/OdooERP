# -- coding: utf-8 --
from odoo.exceptions import ValidationError, UserError

from odoo import models, fields, api, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    hide_imei_fields = fields.Boolean(
        compute='_compute_show_imei_column',
        store=False, tracking=True
    )

    @api.depends('product_id.categ_id')
    def _compute_show_imei_column(self):
        for move in self:
            external_id = ""
            category = move.product_id.categ_id
            if category:
                external_ids = category.get_external_id()
                external_id = external_ids.get(category.id, "")
            # Set field to True only for mobile category
            move.hide_imei_fields = (external_id == 'ks_product_master.product_category_type_mobile')

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

    def action_apply_csv_serial_lines(self, csv_rows, keep_lines=False):
        """Create or update move lines from CSV rows (server-side). Each row: {lot_name, imei, imei2}."""
        self.ensure_one()
        if not self.product_id:
            raise UserError(_("No product found to generate Serials/Lots for."))
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
            loc_dest = self.env["stock.location"].browse(default_vals["location_dest_id"])
            product = self.env["product.product"].browse(default_vals["product_id"])
            loc_dest = loc_dest._get_putaway_strategy(product, 1)
            line_vals = {
                **default_vals,
                "lot_name": lot_name,
                "quantity": 1,
                "location_dest_id": loc_dest.id,
                "product_uom_id": product.uom_id.id,
                "imei": imei,
                "imei2": imei2,
            }
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
        """Generate move line values from CSV rows. Each row is [lot_name, imei, imei2].
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

        vals_list = []
        for row in csv_rows:
            lot_name = (row.get('lot_name') or row.get('serial') or '').strip()
            if not lot_name:
                continue
            imei = (row.get('imei') or row.get('imei1') or '').strip()
            imei2 = (row.get('imei2') or '').strip()
            loc_dest = self.env['stock.location'].browse(default_vals['location_dest_id'])
            product = self.env['product.product'].browse(default_vals['product_id'])
            loc_dest = loc_dest._get_putaway_strategy(product, 1)
            line_vals = {
                **default_vals,
                'lot_name': lot_name,
                'quantity': 1,
                'location_dest_id': loc_dest.id,
                'product_uom_id': product.uom_id.id,
                'imei': imei or False,
                'imei2': imei2 or False,
            }
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


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    imei = fields.Char(string="IMEI 1", compute="_compute_imei", store=True, readonly=False)
    imei2 = fields.Char(string='IMEI 2', compute="_compute_imei", store=True, readonly=False)

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

    def _compute_imei(self):

        for line in self:
            if line.move_id.picking_id.picking_type_id.code == 'incoming':
                return
        for line in self:
            quant = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.location_id.id),
                ('lot_id', '=', line.lot_id.id),
            ], limit=1)
            line.imei = quant.imei if quant else False
            line.imei2 = quant.imei2 if quant else False

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

                if specs_made_id and quant.specs_made and quant.specs_made.id != specs_made_id:
                    raise ValidationError(_('The selected quant has a different "Spec Made For" (%s) than required (%s).') %
                                        (quant.specs_made.name, specs_made.name))
                if made_country_id and quant.made_country and quant.made_country.id != made_country_id:
                    raise ValidationError(_('The selected quant has a different "Made In" (%s) than required (%s).') %
                                        (quant.made_country.name, made_country.name))
        
        res = super().write(vals)
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
                if specs_made and quant.specs_made and quant.specs_made.id != specs_made.id:
                    raise ValidationError(_('The selected quant has a different "Spec Made For" (%s) than required (%s).') % 
                                        (quant.specs_made.name, specs_made.name))
                if made_country and quant.made_country and quant.made_country.id != made_country.id:
                    raise ValidationError(_('The selected quant has a different "Made In" (%s) than required (%s).') % 
                                        (quant.made_country.name, made_country.name))
        
        move_lines = super().create(vals_list)
        for line in move_lines:
            # Propagate country fields from move to move line if not already set
            if line.move_id:
                if not line.specs_made and line.move_id.specs_made:
                    line.specs_made = line.move_id.specs_made.id
                if not line.made_country and line.move_id.made_country:
                    line.made_country = line.move_id.made_country.id
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
                brand_record = record.product_id.product_tmpl_id.brand_id
                brand_name = brand_record.name
                is_brand_samsung_or_oneplus = False
                if brand_name and (brand_name.lower() == 'samsung' or brand_name.lower() == 'oneplus'):
                    is_brand_samsung_or_oneplus = True

                if not is_brand_samsung_or_oneplus:
                    if record.imei == record.imei2:
                        raise ValidationError(
                            f"Both IMEI numbers must be different for product '{record.product_id.product_tmpl_id.name}'")

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
        help='Country where the product is manufactured',
        tracking=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        for picking in pickings:
            if picking.specs_made and picking.made_country and picking.picking_type_id.code == 'outgoing':
                picking._update_move_quantities_by_country_stock()
        return pickings

    def write(self, vals):
        res = super().write(vals)
        if 'specs_made' in vals or 'made_country' in vals:
            for picking in self:
                if picking.specs_made and picking.made_country and picking.picking_type_id.code == 'outgoing':
                    picking._update_move_quantities_by_country_stock()
        return res

    def action_confirm(self):
        """Override to propagate specs_made and made_country to moves and move lines"""
        res = super().action_confirm()
        self._propagate_country_fields_to_moves()
        return res

    def _propagate_country_fields_to_moves(self):
        """Propagate specs_made and made_country from picking to related moves and move lines"""
        for picking in self:
            if picking.specs_made or picking.made_country:
                # Update all moves
                picking.move_ids.write({
                    'specs_made': picking.specs_made.id if picking.specs_made else False,
                    'made_country': picking.made_country.id if picking.made_country else False,
                })
                # Update all move lines
                picking.move_line_ids.write({
                    'specs_made': picking.specs_made.id if picking.specs_made else False,
                    'made_country': picking.made_country.id if picking.made_country else False,
                })

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
        """When Spec Made For or Made In change, update product line quantities and line serial/IMEI to available stock (in-memory)."""
        if self.specs_made and self.made_country and self.picking_type_id.code == 'outgoing':
            for move, assign_qty in self._get_country_stock_assign_quantities():
                move.product_uom_qty = assign_qty
            self._assign_move_line_quants_by_country_fields(persist=False)

    def button_validate(self):
        """Override to validate country fields, assign matching quants, and propagate before validation"""
        # Validate that required fields are populated
        for picking in self:
            if picking.state in ('draft', 'waiting', 'confirmed', 'assigned'):
                if not picking.specs_made:
                    raise ValidationError(_('Please set "Spec Made For" field before validating the delivery order.'))
                if not picking.made_country:
                    raise ValidationError(_('Please set "Made In" field before validating the delivery order.'))
        
        # Assign matching quants based on country fields and validate
        for picking in self:
            picking._assign_quants_by_country_fields()
        
        # Propagate fields to moves and move lines before validation
        self._propagate_country_fields_to_moves()
        
        packaging_category = self.env.ref('ks_product_master.product_category_type_packaging_material',
                                          raise_if_not_found=False)

        for picking in self:
            for line in picking.move_line_ids:
                product = line.product_id
                category = product.categ_id
                if line.picking_type_id.code != 'outgoing' and category != packaging_category:  # dont validate if it's outgoing picking (sales order)
                    line.validate_imei_and_serial_number()
        return super().button_validate()

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
