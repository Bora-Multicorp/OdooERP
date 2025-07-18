from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()

        for picking in self:
            if picking.picking_type_code != 'outgoing' or picking.state != 'done':
                continue

            source_location = picking.location_id
            destination_location = self.env['stock.location'].search([
                ('usage', '=', 'inventory'),
                ('name', '=', 'Virtual Locations')
            ], limit=1)

            if not destination_location:
                raise UserError("Virtual Location not found!")

            internal_picking_type = self.env.ref('stock.picking_type_internal')

            already_exists = self.env['stock.picking'].search([
                ('origin', '=', picking.name),
                ('picking_type_id', '=', internal_picking_type.id)
            ], limit=1)
            if already_exists:
                continue

            move_lines = []

            for move in picking.move_ids_without_package:
                product = move.product_id
                qty = move.product_uom_qty or 0.0
                tmpl = product.product_tmpl_id
                weight = tmpl.weight or 0.0
                packing_lines = tmpl.packing_material_line_ids

                # ➤ Get box products by type
                box_map = {line.box_type: line.packing_material_id for line in packing_lines if line.box_type}

                # ➤ Count total regular boxes needed
                total_regular_boxes = 0
                for line in packing_lines:
                    if line.box_type == 'regular':
                        if line.apply_by == 'unit':
                            total_regular_boxes += int(qty * line.qty_per_unit)
                        elif line.apply_by == 'weight':
                            total_regular_boxes += int(weight * qty * line.qty_per_unit)

                # ➤ Add regular box lines
                if box_map.get('regular') and total_regular_boxes:
                    move_lines.append((0, 0, {
                        'name': box_map['regular'].name,
                        'product_id': box_map['regular'].id,
                        'product_uom_qty': total_regular_boxes,
                        'product_uom': box_map['regular'].uom_id.id,
                        'location_id': source_location.id,
                        'location_dest_id': destination_location.id,
                    }))

                # ➤ Add large and x-large box lines based on regular box count
                reg_per_xlarge = 4
                reg_per_large = 2

                num_xlarge = total_regular_boxes // reg_per_xlarge
                rem_after_xlarge = total_regular_boxes % reg_per_xlarge

                num_large = rem_after_xlarge // reg_per_large

                if box_map.get('xlarge') and num_xlarge:
                    move_lines.append((0, 0, {
                        'name': box_map['xlarge'].name,
                        'product_id': box_map['xlarge'].id,
                        'product_uom_qty': num_xlarge,
                        'product_uom': box_map['xlarge'].uom_id.id,
                        'location_id': source_location.id,
                        'location_dest_id': destination_location.id,
                    }))
                if box_map.get('large') and num_large:
                    move_lines.append((0, 0, {
                        'name': box_map['large'].name,
                        'product_id': box_map['large'].id,
                        'product_uom_qty': num_large,
                        'product_uom': box_map['large'].uom_id.id,
                        'location_id': source_location.id,
                        'location_dest_id': destination_location.id,
                    }))

                # ➤ Add bubble wrap and other extra materials
                for line in packing_lines:
                    # Skip lines already handled (boxes)
                    if line.box_type:
                        continue

                    # Skip tapes
                    if "tape" in line.packing_material_id.name.lower():
                        continue

                    # Calculate quantity
                    used_qty = 0.0
                    if line.apply_by == 'unit':
                        used_qty = qty * line.qty_per_unit
                    elif line.apply_by == 'weight':
                        used_qty = weight * qty * line.qty_per_unit

                    if used_qty > 0:
                        move_lines.append((0, 0, {
                            'name': line.packing_material_id.name,
                            'product_id': line.packing_material_id.id,
                            'product_uom_qty': used_qty,
                            'product_uom': line.packing_material_id.uom_id.id,
                            'location_id': source_location.id,
                            'location_dest_id': destination_location.id,
                        }))

            # ➤ Create internal picking for packing materials
            if move_lines:
                internal_picking = self.env['stock.picking'].create({
                    'picking_type_id': internal_picking_type.id,
                    'location_id': source_location.id,
                    'location_dest_id': destination_location.id,
                    'origin': picking.name,
                    'move_type': 'direct',
                    'move_ids_without_package': move_lines,
                })

                internal_picking.action_confirm()
                internal_picking.action_assign()

                for move in internal_picking.move_ids_without_package:
                    move.quantity = move.product_uom_qty

                internal_picking.button_validate()

        return res
