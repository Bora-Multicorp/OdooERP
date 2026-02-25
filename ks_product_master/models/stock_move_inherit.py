# -- coding: utf-8 --
from odoo.exceptions import ValidationError

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
                # Check if move line has country fields set
                specs_made = line.specs_made or (line.move_id and line.move_id.specs_made)
                made_country = line.made_country or (line.move_id and line.move_id.made_country)
                
                if specs_made and quant.specs_made and quant.specs_made.id != specs_made.id:
                    raise ValidationError(_('The selected quant has a different "Spec Made For" (%s) than required (%s).') % 
                                        (quant.specs_made.name, specs_made.name))
                if made_country and quant.made_country and quant.made_country.id != made_country.id:
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
            
            if not quant:
                # No matching quant found
                missing_quants.append(
                    _('Product: %s - No inventory found matching Spec Made For: %s and Made In: %s') % 
                    (move_line.product_id.display_name, self.specs_made.name, self.made_country.name)
                )
                continue
            
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
