# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import format_date


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    pickup_date = fields.Datetime(
        string='Pick-Up Date',
        copy=False,
    )
    transporter_id = fields.Many2one(
        'res.partner',
        string='Transporter',
        domain="[('category_id.name', 'ilike', 'transporter')]",
        check_company=True,
        copy=False,
    )
    carrier_tracking_ref = fields.Char(
        string='Tracking Reference/Docket Number',
        copy=False,
    )

    # 1(c) Docket LR Copy (document upload with preview)
    docket_lr_copy = fields.Many2many(
        'ir.attachment',
        'stock_picking_docket_lr_rel',
        'picking_id',
        'attachment_id',
        string='Docket LR Copy',
    )
    # 3(c) Amount (float)
    amount = fields.Float(
        string='Amount',
    )
    # 2(c) Additional details (html)
    additional_details = fields.Html(
        string='Additional details',
    )

    vendor_bill_id = fields.Many2one(
        'account.move',
        string='Vendor Bill',
        copy=False,
        readonly=True,
    )

    # Inspection at Pick-up point: 1(i) Fresh/Activated
    fresh_activated = fields.Selection(
        [
            ('matched', 'Matched'),
            ('not_matched', 'Not Matched'),
        ],
        string='Fresh/Activated',
    )
    fresh_activated_remark = fields.Text(
        string='Remark',
    )

    # Inspection at Pick-up point: 2(i) Loose/Master
    loose_master = fields.Selection(
        [
            ('matched', 'Matched'),
            ('not_matched', 'Not Matched'),
        ],
        string='Loose/Master',
    )
    loose_master_remark = fields.Text(
        string='Remark',
    )

    # Inspection at Pick-up point: 3(i) Inspection Condition
    inspection_condition = fields.Selection(
        [
            ('neat_and_clean', 'Neat and Clean'),
            ('damage', 'Damage'),
            ('box_press', 'Box Press'),
        ],
        string='Inspection Condition',
    )
    inspection_condition_remark = fields.Text(
        string='Remark',
    )

    # Documents Section: 1(d) E- Invoice
    e_invoice = fields.Many2many(
        'ir.attachment',
        'stock_picking_e_invoice_rel',
        'picking_id',
        'attachment_id',
        string='E- Invoice',
    )
    # Documents Section: 2(d) E-way bill
    eway_bill = fields.Many2many(
        'ir.attachment',
        'stock_picking_eway_bill_rel',
        'picking_id',
        'attachment_id',
        string='E-way bill',
    )
    # Documents Section: 3(d) IMEI sheet
    imei_sheet = fields.Many2many(
        'ir.attachment',
        'stock_picking_imei_sheet_rel',
        'picking_id',
        'attachment_id',
        string='IMEI sheet',
    )

    @api.constrains('pickup_date', 'transporter_id', 'carrier_tracking_ref', 'fresh_activated', 'loose_master', 'inspection_condition')
    def _check_pickup_details_mandatory_fields(self):
        for picking in self:
            if picking.picking_type_code == 'incoming' and picking.pickup_date:
                if not picking.transporter_id:
                    raise ValidationError(_("Transporter is required when Pick-Up Date is set."))
                if not picking.carrier_tracking_ref:
                    raise ValidationError(_("Tracking Reference/Docket Number is required when Pick-Up Date is set."))
                if not picking.fresh_activated:
                    raise ValidationError(_("Fresh/Activated is required when Pick-Up Date is set."))
                if not picking.loose_master:
                    raise ValidationError(_("Loose/Master is required when Pick-Up Date is set."))
                if not picking.inspection_condition:
                    raise ValidationError(_("Inspection Condition is required when Pick-Up Date is set."))

    def _get_freight_service_product(self):
        """Retrieve pre-selected service product 'freight charges 18%'."""
        Product = self.env['product.product']
        # 1. Search by default_code 'ALL-CHAR18FRE'
        product = Product.search([('default_code', '=', 'ALL-CHAR18FRE')], limit=1)
        if product:
            return product
        # 2. Search by product template ID 21086
        tmpl = self.env['product.template'].browse(21086)
        if tmpl.exists() and tmpl.product_variant_ids:
            return tmpl.product_variant_ids[0]
        # 3. Search by name 'FREIGHT CHARGES - 18%'
        product = Product.search([('name', '=ilike', 'FREIGHT CHARGES - 18%')], limit=1)
        if product:
            return product
        # 4. Fallback search by keywords
        product = Product.search([('name', 'ilike', 'freight charges'), ('name', 'ilike', '18%')], limit=1)
        if product:
            return product
        return False

    def _get_odoobot_user(self):
        """Find OdooBot user for bill creation."""
        bot_user = self.env.ref('base.user_bot', raise_if_not_found=False) or \
                   self.env.ref('base.user_root', raise_if_not_found=False) or \
                   self.env['res.users'].search([('login', 'in', ['odoobot', '__system__'])], limit=1)
        if not bot_user:
            bot_user = self.env.user
        return bot_user

    def action_create_vendor_bill(self):
        """
        Create or update draft vendor bill for the transporter:
        - Check if any existing draft bill is available with that partner name (transporter) and company.
        - If multiple draft bills exist, selects only the latest created draft bill.
        - If not, create a new vendor bill in draft status (user: odoobot).
        - Add pre-selected service product 'freight charges 18%' with quantity 1 and unit price from picking.amount.
        - Line description: '<carrier_tracking_ref>(<pickup_date dd/MM/yyyy>)'.
        - Amount and total amount are updated automatically.
        """
        self.ensure_one()
        if self.picking_type_code != 'incoming':
            raise ValidationError(_("Vendor Bill can only be created for Receipts (incoming shipments)."))
        if self.state in ('done', 'cancel'):
            raise ValidationError(_("You cannot create a shipment bill for a receipt that is done or cancelled."))
        if not self.pickup_date:
            raise ValidationError(_("Please provide a Pick-Up Date before creating a Vendor Bill."))
        if not self.transporter_id:
            raise ValidationError(_("Please select a Transporter before creating a Vendor Bill."))
        if not self.carrier_tracking_ref:
            raise ValidationError(_("Please provide a Tracking Reference/Docket Number before creating a Vendor Bill."))
        if self.amount <= 0.0:
            raise ValidationError(_("Please provide an Amount greater than 0 before creating a Vendor Bill."))

        product = self._get_freight_service_product()
        if not product:
            raise ValidationError(_("Service product 'FREIGHT CHARGES - 18%' was not found in the system."))

        bot_user = self._get_odoobot_user()

        # Description: Tracking reference/Docket number concatenated with pickup date (dd/MM/yyyy)
        date_str = format_date(self.env, self.pickup_date, date_format='dd/MM/yyyy')
        description = f"{self.carrier_tracking_ref}({date_str})"

        # 1. If this picking already has an active draft bill linked, reuse it
        existing_bill = False
        if self.vendor_bill_id and self.vendor_bill_id.state == 'draft':
            existing_bill = self.vendor_bill_id

        # 2. Gather matching partner IDs (transporter, commercial partner, child contacts, and same name)
        if not existing_bill:
            partner = self.transporter_id
            commercial_partner = partner.commercial_partner_id or partner
            partner_ids = set([partner.id, commercial_partner.id])
            if commercial_partner.child_ids:
                partner_ids.update(commercial_partner.child_ids.ids)
            # Also find partners with matching name (case-insensitive)
            same_name_partners = self.env['res.partner'].sudo().search([
                ('name', '=ilike', partner.name)
            ])
            partner_ids.update(same_name_partners.ids)
            partner_ids = list(partner_ids)

            # Step A: Search for latest draft bill for this partner in the SAME company
            existing_bill = self.env['account.move'].sudo().search([
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'draft'),
                ('partner_id', 'in', partner_ids),
                ('company_id', '=', self.company_id.id),
            ], order='create_date desc, id desc', limit=1)

            # Step B: If not found, search within company branch/hierarchy
            if not existing_bill:
                root_company = self.company_id.root_id or self.company_id
                existing_bill = self.env['account.move'].sudo().search([
                    ('move_type', '=', 'in_invoice'),
                    ('state', '=', 'draft'),
                    ('partner_id', 'in', partner_ids),
                    ('company_id', 'child_of', root_company.id),
                ], order='create_date desc, id desc', limit=1)

            # Step C: If still not found, search across the entire system
            if not existing_bill:
                existing_bill = self.env['account.move'].sudo().search([
                    ('move_type', '=', 'in_invoice'),
                    ('state', '=', 'draft'),
                    ('partner_id', 'in', partner_ids),
                ], order='create_date desc, id desc', limit=1)

        if existing_bill:
            bill = existing_bill
        else:
            move_vals = {
                'move_type': 'in_invoice',
                'partner_id': self.transporter_id.id,
                'company_id': self.company_id.id,
                'invoice_user_id': bot_user.id,
            }
            bill = self.env['account.move'].with_company(self.company_id).with_user(bot_user).sudo().create(move_vals)

        # Check if line for this exact docket/date description and product already exists on this bill
        bill_company = bill.company_id or self.company_id
        existing_line = bill.invoice_line_ids.filtered(
            lambda l: l.product_id.id == product.id and l.name == description
        )
        if existing_line:
            existing_line.with_company(bill_company).with_user(bot_user).sudo().write({
                'price_unit': self.amount,
                'quantity': 1.0,
            })
        else:
            line_vals = {
                'move_id': bill.id,
                'product_id': product.id,
                'quantity': 1.0,
                'price_unit': self.amount,
                'name': description,
            }
            self.env['account.move.line'].with_company(bill_company).with_user(bot_user).sudo().create(line_vals)

        self.vendor_bill_id = bill.id

        return {
            'name': _('Vendor Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': bill.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_vendor_bill(self):
        self.ensure_one()
        if not self.vendor_bill_id:
            raise ValidationError(_("No Vendor Bill linked to this receipt."))
        return {
            'name': _('Vendor Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.vendor_bill_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
