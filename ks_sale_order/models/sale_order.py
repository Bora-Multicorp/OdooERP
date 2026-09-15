# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_status = fields.Selection(
        selection=[
            ('no_invoice', 'No Invoice'),
            ('unpaid', 'Unpaid'),
            ('partial', 'Partial'),
            ('paid', 'Paid'),
        ],
        string='Payment Status',
        compute='_compute_payment_status',
        store=True,
        readonly=True,
        copy=False,
        help='Payment status: total_invoice_payment_received + ks_advance_payment_amount vs order amount_total.',
    )

    ks_bank_id = fields.Many2one(
        'res.bank',
        string='Bank Information',
        copy=False,
        help='Bank details for this Sale Order.',
    )

    ks_enable_shipping_cash_charges = fields.Boolean(
        related='company_id.ks_enable_shipping_cash_charges',
        string="Enable Cash Handling & Transfer Charges",
    )
    has_cash_handling_charge = fields.Boolean(
        string="Has Cash Handling Charge",
        compute="_compute_charge_line_presence",
    )
    has_transfer_charge = fields.Boolean(
        string="Has Transfer Charge",
        compute="_compute_charge_line_presence",
    )

    def _is_cash_handling_product(self, product):
        if not product:
            return False
        name = (product.name or '').upper().strip()
        code = (product.default_code or '').upper().strip()
        return 'CASH HANDLING' in name or 'CASH-HANDLING' in code or code == 'CASH-HANDLING'

    def _is_transfer_charge_product(self, product):
        if not product:
            return False
        name = (product.name or '').upper().strip()
        code = (product.default_code or '').upper().strip()
        return 'TRANSFER' in name or 'TRANSFER-CHARGES' in code or code == 'TRANSFER-CHARGES'

    @api.depends('order_line', 'order_line.product_id')
    def _compute_charge_line_presence(self):
        for order in self:
            order.has_cash_handling_charge = any(
                order._is_cash_handling_product(line.product_id) or line.is_cash_handling_charge
                for line in order.order_line
            )
            order.has_transfer_charge = any(
                order._is_transfer_charge_product(line.product_id) or line.is_transfer_charge
                for line in order.order_line
            )

    def _ks_get_or_create_charge_product(self, xml_id, default_name, default_code):
        """Helper to find or create service product for charges."""
        # 1. Try search product.product directly by default_code or name
        variant = self.env['product.product'].search([('default_code', '=', default_code)], limit=1)
        if not variant:
            variant = self.env['product.product'].search([('name', '=', default_name)], limit=1)
        if variant:
            tmpl = variant.product_tmpl_id
            updates = {}
            if tmpl.type != 'service':
                updates['type'] = 'service'
            if hasattr(tmpl, 'is_storable') and tmpl.is_storable:
                updates['is_storable'] = False
            if hasattr(tmpl, 'tracking') and tmpl.tracking != 'none':
                updates['tracking'] = 'none'
            if not tmpl.sale_ok:
                updates['sale_ok'] = True
            if tmpl.purchase_ok:
                updates['purchase_ok'] = False
            if updates:
                tmpl.sudo().write(updates)
            return variant

        # 2. Try search product.template by xml_id, default_code, or name
        product_template = self.env.ref(xml_id, raise_if_not_found=False)
        if not product_template:
            product_template = self.env['product.template'].search([
                '|', ('default_code', '=', default_code), ('name', '=', default_name)
            ], limit=1)
        if not product_template:
            create_vals = {
                'name': default_name,
                'default_code': default_code,
                'type': 'service',
                'invoice_policy': 'order',
                'sale_ok': True,
                'purchase_ok': False,
            }
            if hasattr(self.env['product.template'], 'is_storable'):
                create_vals['is_storable'] = False
            if hasattr(self.env['product.template'], 'tracking'):
                create_vals['tracking'] = 'none'
            product_template = self.env['product.template'].create(create_vals)
        else:
            updates = {}
            if product_template.type != 'service':
                updates['type'] = 'service'
            if hasattr(product_template, 'is_storable') and product_template.is_storable:
                updates['is_storable'] = False
            if hasattr(product_template, 'tracking') and product_template.tracking != 'none':
                updates['tracking'] = 'none'
            if not product_template.sale_ok:
                updates['sale_ok'] = True
            if product_template.purchase_ok:
                updates['purchase_ok'] = False
            if updates:
                product_template.sudo().write(updates)

        # 3. Get variant from template or create one if missing
        variant = product_template.product_variant_ids[:1]
        if not variant:
            variant = self.env['product.product'].search([('product_tmpl_id', '=', product_template.id)], limit=1)
        if not variant:
            variant = self.env['product.product'].create({
                'product_tmpl_id': product_template.id,
                'default_code': default_code,
            })
        return variant

    def action_add_cash_handling_charge(self):
        """Add Cash Handling Charge line to sale order. Silently skips if already present."""
        self.ensure_one()
        if not self.company_id.ks_enable_shipping_cash_charges:
            return

        # Live check: silently skip if Cash Handling Charge line is already present
        if any(self._is_cash_handling_product(line.product_id) or line.is_cash_handling_charge for line in self.order_line):
            return

        product = self._ks_get_or_create_charge_product(
            'ks_sale_order.product_template_cash_handling_charges',
            'CASH HANDLING CHARGES',
            'CASH-HANDLING'
        )
        if not product or not product.id:
            return

        if any(line.product_id == product for line in self.order_line):
            return

        base_amount = sum(
            line.price_subtotal for line in self.order_line
            if not line.display_type and not self._is_cash_handling_product(line.product_id) and not self._is_transfer_charge_product(line.product_id)
        )
        charge_type = self.company_id.ks_cash_handling_charge_type or 'percentage'
        val = self.company_id.ks_cash_handling_charge_value or self.company_id.ks_cash_handling_charge_pct or 0.0
        currency_name = self.currency_id.name or self.company_id.currency_id.name or ''

        if charge_type == 'fixed':
            charge_amount = val
            line_description = _("Cash Handling Charges (%(amount)g %(currency)s Flat)", amount=charge_amount, currency=currency_name)
        else:
            charge_amount = base_amount * (val / 100.0)
            line_description = _("Cash Handling Charges (%(pct)g%% - %(currency)s)", pct=val, currency=currency_name)

        line_vals = {
            'order_id': self.id,
            'product_id': product.id,
            'name': line_description,
            'product_uom_qty': 1.0,
            'price_unit': charge_amount,
        }
        if product.product_tmpl_id:
            line_vals['product_template_id'] = product.product_tmpl_id.id
        if product.uom_id:
            line_vals['product_uom'] = product.uom_id.id

        self.env['sale.order.line'].create(line_vals)
        self.invalidate_recordset(['order_line', 'has_cash_handling_charge', 'has_transfer_charge'])
        self._compute_charge_line_presence()
        return

    def action_add_transfer_charge(self):
        """Add Transfer Charge line to sale order. Silently skips if already present."""
        self.ensure_one()
        if not self.company_id.ks_enable_shipping_cash_charges:
            return

        # Live check: silently skip if Transfer Charge line is already present
        if any(self._is_transfer_charge_product(line.product_id) or line.is_transfer_charge for line in self.order_line):
            return

        product = self._ks_get_or_create_charge_product(
            'ks_sale_order.product_template_transfer_charges',
            'TRANSFER CHARGES',
            'TRANSFER-CHARGES'
        )
        if not product or not product.id:
            return

        if any(line.product_id == product for line in self.order_line):
            return

        flat_amount = self.company_id.ks_transfer_charge_amount or 0.0
        currency_name = self.currency_id.name or self.company_id.currency_id.name or ''
        line_description = _("Transfer Charges (%(amount)g %(currency)s Flat)", amount=flat_amount, currency=currency_name)

        line_vals = {
            'order_id': self.id,
            'product_id': product.id,
            'name': line_description,
            'product_uom_qty': 1.0,
            'price_unit': flat_amount,
        }
        if product.product_tmpl_id:
            line_vals['product_template_id'] = product.product_tmpl_id.id
        if product.uom_id:
            line_vals['product_uom'] = product.uom_id.id

        self.env['sale.order.line'].create(line_vals)
        self.invalidate_recordset(['order_line', 'has_cash_handling_charge', 'has_transfer_charge'])
        self._compute_charge_line_presence()
        return


    def _prepare_invoice(self):
        """Copy ks_bank_id from sale order to invoice."""
        invoice_vals = super()._prepare_invoice()
        if self.ks_bank_id:
            invoice_vals['ks_bank_id'] = self.ks_bank_id.id
        return invoice_vals

    @api.depends(
        'amount_total',
        'total_invoice_payment_received',
        'ks_advance_payment_amount',
        'order_line.invoice_lines.move_id.state',
    )
    def _compute_payment_status(self):
        """Compute payment status from total payment received vs order amount_total.
        Total payment = total_invoice_payment_received (from ks_sale_advance_payment) + ks_advance_payment_amount.
        - no_invoice: no posted invoices and no payment received (invoice + advance = 0).
        - paid: total payment received >= order amount_total.
        - partial: some payment received but total < order amount_total.
        - unpaid: posted invoices exist but no payment received yet.
        """
        for order in self:
            invoice_paid = getattr(order, 'total_invoice_payment_received', None) or 0.0
            advance_paid = getattr(order, 'ks_advance_payment_amount', None) or 0.0
            paid_amount = invoice_paid + advance_paid
            order_total = order.amount_total or 0.0

            invoices = order.invoice_ids
            posted = invoices.filtered(lambda m: m.state == 'posted')

            if not posted and float_compare(paid_amount, 0.0, precision_digits=2) <= 0:
                order.payment_status = 'no_invoice'
            elif order_total <= 0:
                order.payment_status = 'paid' if float_compare(paid_amount, 0.0, precision_digits=2) > 0 else 'unpaid'
            elif float_compare(paid_amount, order_total, precision_digits=2) >= 0:
                order.payment_status = 'paid'
            elif float_compare(paid_amount, 0.0, precision_digits=2) > 0:
                order.payment_status = 'partial'
            else:
                order.payment_status = 'unpaid'

    # Fields to track PO creation and notifications
    ks_po_created_for_stock = fields.Boolean(
        string='PO Created for Stock',
        default=False,
        copy=False,
        help='Indicates if a Purchase Order was created for out-of-stock products'
    )
    ks_created_po_id = fields.Many2one(
        'purchase.order',
        string='Created Purchase Order',
        copy=False,
        readonly=True,
        help='Purchase Order created for out-of-stock products (if single PO)'
    )
    ks_created_po_ids = fields.One2many(
        'purchase.order',
        'ks_source_sale_order_id',
        string='Created Purchase Orders',
        readonly=True,
        help='All Purchase Orders created for out-of-stock products'
    )
    ks_created_po_count = fields.Integer(
        string='Purchase Orders Count',
        compute='_compute_ks_created_po_count',
        help='Number of Purchase Orders created for this Sale Order'
    )
    
    @api.depends('ks_created_po_ids')
    def _compute_ks_created_po_count(self):
        """Compute the count of created Purchase Orders"""
        for order in self:
            order.ks_created_po_count = len(order.ks_created_po_ids)
    
    def action_view_created_purchase_orders(self):
        """Open the created Purchase Orders"""
        self.ensure_one()
        if not self.ks_created_po_ids:
            return False
        
        if len(self.ks_created_po_ids) == 1:
            return {
                'name': 'Purchase Order',
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'form',
                'res_id': self.ks_created_po_ids.id,
                'target': 'current',
            }
        else:
            return {
                'name': 'Purchase Orders',
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', self.ks_created_po_ids.ids)],
                'target': 'current',
            }
    ks_has_insufficient_stock = fields.Boolean(
        string='Has Insufficient Stock',
        compute='_compute_has_insufficient_stock',
        help='True if any product in the order has insufficient stock'
    )

    def _ks_validate_stock_for_confirmation(self):
        """Validate stock availability for all lines before confirming the order.
        
        Checks each order line's product quantity against available stock in the same company.
        - If stock is available in same company: allows confirmation silently (no warning/email/message)
        - If stock is NOT available in same company: blocks confirmation
          - If stock is available in other companies: shows message about other companies
          - Existing email/message notifications continue as before
        
        Raises:
            UserError: If any product has insufficient stock in the same company
        """
        self.ensure_one()
        
        insufficient_products = []
        products_available_in_other_companies = []
        
        for line in self.order_line:
            # Skip display type lines (sections, notes)
            if line.display_type:
                continue
            
            # Skip non-storable products
            if not line.product_id or not line.product_id.is_storable:
                continue
            
            # Check availability in same company - use Sale Order's warehouse if available
            is_available, available_qty = line._ks_check_product_availability(
                line.product_id, 
                line.product_uom_qty, 
                self.company_id,
                warehouse=self.warehouse_id if hasattr(self, 'warehouse_id') and self.warehouse_id else None
            )
            
            if not is_available:
                insufficient_products.append({
                    'product': line.product_id.display_name,
                    'product_id': line.product_id,
                    'requested': line.product_uom_qty,
                    'available': available_qty,
                })
                
                # Check if available in other companies
                other_companies = line._ks_check_product_availability_other_companies(
                    line.product_id,
                    line.product_uom_qty,
                    self.company_id
                )
                
                if other_companies:
                    products_available_in_other_companies.append({
                        'product': line.product_id.display_name,
                        'companies': other_companies,
                    })
        
        # If all products have stock in same company, allow confirmation silently
        if not insufficient_products:
            return
        
        # Stock is insufficient in same company - block confirmation
        # Build error message with all insufficient products
        error_lines = []
        for item in insufficient_products:
            error_lines.append(
                _("• %(product)s: Requested %(requested)s, Available %(available)s",
                  product=item['product'],
                  requested=item['requested'],
                  available=item['available'])
            )
        
        error_msg = _(
            "Cannot confirm order! Insufficient stock for the following products:\n\n"
            "%(products)s\n\n"
            "Company: %(company)s\n\n"
            "Please adjust the quantities or replenish stock before confirming this order.",
            products='\n'.join(error_lines),
            company=self.company_id.name,
        )
        
        # Post message about products available in other companies
        if products_available_in_other_companies:
            other_companies_msg_lines = []
            for item in products_available_in_other_companies:
                company_names = ', '.join([c['company'] for c in item['companies']])
                other_companies_msg_lines.append(
                    _("• %(product)s is available in: %(companies)s",
                      product=item['product'],
                      companies=company_names)
                )
            
            other_companies_msg = _(
                "Note: The following products are available in other companies:\n"
                "%(products)s\n\n"
                "However, stock must be available in %(company)s to confirm this order.",
                products='\n'.join(other_companies_msg_lines),
                company=self.company_id.name
            )
            
            # Post message in order history (chatter)
            self.message_post(
                body=other_companies_msg,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        
        # Raise error to block confirmation
        raise UserError(error_msg)

    @api.onchange('partner_id')
    def _onchange_partner_id_overseas_kyc(self):
        """
        Non-blocking warning shown immediately when a salesperson selects an
        overseas customer whose KYC is not yet approved.

        Vendor partners are skipped — their KYC blocking is handled separately
        and must remain unchanged.
        """
        if not self.partner_id:
            return
        # Skip partners that are vendors — existing vendor KYC logic handles them
        if self.partner_id.supplier_rank > 0 and not self.partner_id.customer_rank:
            return
        if self.partner_id._is_overseas_kyc_incomplete():
            return {
                'warning': {
                    'title': _('KYC Incomplete — Overseas Customer'),
                    'message': _(
                        'The customer "%s" is marked as an Overseas Customer but '
                        'their KYC verification has not been approved yet.\n\n'
                        'You may proceed with this order, but please ensure KYC '
                        'is completed before dispatching goods or processing payment.'
                    ) % self.partner_id.name,
                    'type': 'dialog',
                }
            }

    def _ks_get_overseas_kyc_incomplete_partners(self):
        """
        Return a recordset of orders (from self) whose partner has incomplete
        overseas KYC. Used by action_confirm to decide whether to surface a
        post-confirmation notification.
        """
        return self.filtered(lambda o: o.partner_id._is_overseas_kyc_incomplete())

    def action_confirm(self):
        """Override action_confirm to check stock availability and trigger alerts.

        Stock validation is performed AFTER confirmation:
        - First confirms the order (state changes to 'sale')
        - Then checks all order lines for insufficient stock
        - Sends email notifications to procurement team for all insufficient products
        - Shows alert message if any products have insufficient stock
        - Does NOT block confirmation (allows order to be confirmed)
        - Emails are ONLY sent when order is actually confirmed (state = 'sale')

        Additionally, a non-blocking KYC warning is shown after confirmation when
        the customer is an overseas partner with incomplete KYC. Vendor KYC logic
        is untouched.
        """
        # First, confirm the order (this changes state to 'sale')
        result = super().action_confirm()

        # After confirmation, check stock availability and send notifications
        # Only check orders that were just confirmed (state = 'sale')
        orders_to_check = self.filtered(lambda o: o.state == 'sale')

        # Check stock availability for all lines and send notifications
        for order in orders_to_check:
            order._ks_check_and_notify_stock_shortage_on_confirm()

        # Non-blocking KYC warning for overseas customers with incomplete KYC.
        # The order is already confirmed at this point — this is informational only.
        incomplete_kyc_orders = self._ks_get_overseas_kyc_incomplete_partners()
        if incomplete_kyc_orders:
            partner_names = ', '.join(
                incomplete_kyc_orders.mapped('partner_id.name')
            )
            order_refs = ', '.join(incomplete_kyc_orders.mapped('name'))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('KYC Warning — Overseas Customer(s)'),
                    'message': _(
                        'Order(s) %s confirmed successfully.\n'
                        'Note: Customer(s) %s are marked as Overseas but KYC '
                        'approval is pending. Please complete KYC before '
                        'dispatching goods or processing payment.'
                    ) % (order_refs, partner_names),
                    'type': 'warning',
                    'sticky': True,
                    'next': result,
                },
            }

        return result
    
    def _ks_check_and_notify_stock_shortage_on_confirm(self):
        """Check stock availability for all order lines and send notifications.
        
        This method is called AFTER Sale Order confirmation (state = 'sale') to:
        - Check all order lines for insufficient stock
        - Send email notifications to procurement team for each insufficient product
        - Post messages in chatter about stock shortages
        - Ensure no duplicate notifications are sent
        
        IMPORTANT: This method is ONLY called from action_confirm() AFTER the order
        is confirmed (state = 'sale'). Emails are NOT sent during draft/edit stages.
        """
        self.ensure_one()
        
        # Safety check: Only process confirmed orders (state = 'sale')
        if self.state != 'sale':
            return
        
        # Track which products we've already notified about to prevent duplicates
        notified_products = set()
        insufficient_products = []
        
        # Check all order lines
        for line in self.order_line:
            # Skip display type lines (sections, notes)
            if line.display_type:
                continue
            
            # Skip non-storable products
            if not line.product_id or not line.product_id.is_storable:
                continue
            
            # Skip if we've already notified for this product
            if line.product_id.id in notified_products:
                continue
            
            # CRITICAL: Only send email if delivery is actually blocked (red indicator in Delivered column)
            # The red indicator appears when stock moves cannot be assigned due to insufficient stock
            delivery_blocked = False
            available_qty = 0.0
            
            # Check if stock moves exist and are blocked
            if line.move_ids:
                # Check if any stock moves cannot be fully assigned due to insufficient stock
                for move in line.move_ids:
                    if move.state in ('confirmed', 'waiting', 'partially_available'):
                        # Move cannot be fully assigned - delivery is blocked
                        # In Odoo 18, use move.quantity (reserved qty from move lines) instead of reserved_availability
                        # move.quantity represents the reserved quantity from move_line_ids
                        reserved_qty = move.quantity or 0.0
                        if move.product_uom_qty > reserved_qty:
                            delivery_blocked = True
                            # Get available quantity for the move's source location
                            available_qty = self.env['stock.quant'].with_company(self.company_id.id)._get_available_quantity(
                                move.product_id, move.location_id, allow_negative=False
                            )
                            break
            else:
                # No stock moves created yet - check if stock is insufficient
                # This handles the case where moves haven't been created yet
                is_available, available_qty = line._ks_check_product_availability(
                    line.product_id,
                    line.product_uom_qty,
                    self.company_id,
                    warehouse=self.warehouse_id if hasattr(self, 'warehouse_id') and self.warehouse_id else None
                )
                if not is_available and available_qty < line.product_uom_qty:
                    delivery_blocked = True
            
            # Only send email if delivery is actually blocked (red indicator condition)
            if delivery_blocked:
                # Track this product to avoid duplicate notifications
                notified_products.add(line.product_id.id)
                
                # Collect product info for summary message
                insufficient_products.append({
                    'product': line.product_id.display_name,
                    'requested': line.product_uom_qty,
                    'available': available_qty,
                })
                
                # Send email notification to procurement team ONLY if stock is actually insufficient
                line._ks_send_procurement_notification(
                    line.product_id,
                    line.product_uom_qty,
                    self,
                    available_qty
                )
                
                # Check if available in other companies and post message
                other_companies = line._ks_check_product_availability_other_companies(
                    line.product_id,
                    line.product_uom_qty,
                    self.company_id
                )
                
                if other_companies:
                    company_names = ', '.join([c['company'] for c in other_companies])
                    other_companies_msg = _(
                        "Note: %(product)s is available in other company(ies): %(companies)s\n"
                        "However, stock must be available in %(current_company)s to fulfill this order.",
                        product=line.product_id.display_name,
                        companies=company_names,
                        current_company=self.company_id.name
                    )
                    
                    # Post message in order history (chatter)
                    self.message_post(
                        body=other_companies_msg,
                        message_type='notification',
                        subtype_xmlid='mail.mt_note',
                    )
        
        # Post summary message in chatter if any products have insufficient stock
        if insufficient_products:
            summary_lines = []
            for item in insufficient_products:
                summary_lines.append(
                    _("• %(product)s: Requested %(requested)s, Available %(available)s",
                      product=item['product'],
                      requested=item['requested'],
                      available=item['available'])
                )
            
            summary_msg = _(
                "⚠️ Stock Shortage Alert: The following products have insufficient stock:\n\n"
                "%(products)s\n\n"
                "Email notifications have been sent to the Procurement Team.",
                products='\n'.join(summary_lines)
            )
            
            self.message_post(
                body=summary_msg,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
    
    @api.depends('order_line.product_id', 'order_line.product_uom_qty', 'state')
    def _compute_has_insufficient_stock(self):
        """Compute if the sale order has any products with insufficient stock"""
        for order in self:
            if order.state in ('sale', 'done', 'cancel'):
                order.ks_has_insufficient_stock = False
                continue
            
            has_insufficient = False
            for line in order.order_line:
                # Skip display type lines (sections, notes)
                if line.display_type:
                    continue
                
                # Skip non-storable products
                if not line.product_id or not line.product_id.is_storable:
                    continue
                
                # Check availability - use Sale Order's warehouse if available
                is_available, available_qty = line._ks_check_product_availability(
                    line.product_id,
                    line.product_uom_qty,
                    order.company_id,
                    warehouse=order.warehouse_id if hasattr(order, 'warehouse_id') and order.warehouse_id else None
                )
                
                if not is_available:
                    has_insufficient = True
                    break
            
            order.ks_has_insufficient_stock = has_insufficient
    
    def _ks_get_out_of_stock_products(self):
        """Get list of products with insufficient stock and their details
        
        Returns:
            list: List of dicts with product, quantity, available_qty, vendor info
        """
        self.ensure_one()
        out_of_stock_products = []
        
        for line in self.order_line:
            # Skip display type lines (sections, notes)
            if line.display_type:
                continue
            
            # Skip non-storable products
            if not line.product_id or not line.product_id.is_storable:
                continue
            
            # Check availability - STRICTLY for this Sale Order's company only
            # This ensures we only check stock in the same company as the Sale Order
            # Use the Sale Order's warehouse if available
            is_available, available_qty = line._ks_check_product_availability(
                line.product_id,
                line.product_uom_qty,
                self.company_id,  # Explicitly use Sale Order's company_id
                warehouse=self.warehouse_id if hasattr(self, 'warehouse_id') and self.warehouse_id else None
            )
            
            if not is_available:
                # Get vendor for the product
                product = line.product_id.with_company(self.company_id)
                seller = product._select_seller(
                    quantity=line.product_uom_qty,
                    date=self.date_order and self.date_order.date() or fields.Date.today(),
                    uom_id=product.uom_po_id
                )
                
                vendor = seller.partner_id if seller else False
                
                out_of_stock_products.append({
                    'product_id': line.product_id,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom,
                    'available_qty': available_qty,
                    'vendor': vendor,
                    'seller': seller,
                })
        
        return out_of_stock_products
    
    def _ks_check_and_notify_stock_availability(self):
        """Check if stock is now available and notify SO creator if all products have stock"""
        self.ensure_one()
        
        # Only check if PO was created for stock
        if not self.ks_po_created_for_stock:
            return
        
        # Check if all products now have sufficient stock
        all_available = True
        insufficient_products = []
        
        for line in self.order_line:
            # Skip display type lines (sections, notes)
            if line.display_type:
                continue
            
            # Skip non-storable products
            if not line.product_id or not line.product_id.is_storable:
                continue
            
            # Check availability - STRICTLY for this Sale Order's company only
            # This ensures we only check stock in the same company as the Sale Order
            # Use the Sale Order's warehouse if available
            is_available, available_qty = line._ks_check_product_availability(
                line.product_id,
                line.product_uom_qty,
                self.company_id,  # Explicitly use Sale Order's company_id
                warehouse=self.warehouse_id if hasattr(self, 'warehouse_id') and self.warehouse_id else None
            )
            
            if not is_available:
                all_available = False
                insufficient_products.append({
                    'product': line.product_id.display_name,
                    'requested': line.product_uom_qty,
                    'available': available_qty,
                })
        
        # If all products are now available, notify the SO user/salesperson
        if all_available:
            # Collect recipients: SO creator and salesperson
            recipients = []
            if self.create_uid and self.create_uid.partner_id:
                recipients.append(self.create_uid.partner_id)
            if self.user_id and self.user_id.partner_id and self.user_id.partner_id not in recipients:
                recipients.append(self.user_id.partner_id)
            
            if recipients:
                recipient_partners = [r for r in recipients if r]
                recipient_emails = [r.email for r in recipient_partners if r.email]
                
                # Post message in chatter
                self.message_post(
                    body=_("✅ Stock is now available for your Sale Order!      "
                           "All products now have sufficient stock. You can confirm the Sale Order now."),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                    partner_ids=[r.id for r in recipient_partners],
                )
                
                # Send email notification to recipients
                if recipient_emails:
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    so_url = f"{base_url}/web#id={self.id}&model=sale.order&view_type=form"
                    
                    # Create email body
                    recipient_names = ', '.join([r.name for r in recipient_partners])
                    email_body = _(
                        "<p>Hello %s,</p>"
                        "<p>Good news! Stock is now available for your Sale Order <strong>%s</strong>.</p>"
                        "<p>All products now have sufficient stock. You can confirm the Sale Order now.</p>"
                        "<p><a href='%s'>Click here to view the Sale Order</a></p>"
                        "<p>Best regards,<br/>Odoo System</p>"
                    ) % (recipient_names, self.name or f'SO-{self.id}', so_url)
                    
                    try:
                        mail_values = {
                            'subject': _('Stock Available: Sale Order %s') % (self.name or f'SO-{self.id}'),
                            'body_html': email_body,
                            'email_to': ','.join(recipient_emails),
                            'email_from': self.env.user.email or self.company_id.email or 'noreply@odoo.com',
                            'auto_delete': True,
                            'model': self._name,
                            'res_id': self.id,
                        }
                        mail = self.env['mail.mail'].sudo().create(mail_values)
                        mail.send()
                    except Exception as e:
                        # Log error but don't fail
                        import logging
                        _logger = logging.getLogger(__name__)
                        _logger.warning(
                            "KS Sale Order: Failed to send stock availability email to %s for SO %s: %s",
                            ', '.join(recipient_emails), self.name or f'SO-{self.id}', str(e)
                        )

