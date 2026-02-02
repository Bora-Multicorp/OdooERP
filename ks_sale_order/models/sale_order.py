# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
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

    def action_confirm(self):
        """Override action_confirm to check stock availability and trigger alerts.
        
        Stock validation is performed at confirmation time:
        - Checks all order lines for insufficient stock
        - Sends email notifications to procurement team for all insufficient products
        - Shows alert message if any products have insufficient stock
        - Does NOT block confirmation (allows order to be confirmed)
        - Emails are ONLY sent when order is being confirmed (state transitions to 'sale')
        """
        # Only send stock shortage emails for orders that are not already confirmed
        # This prevents duplicate emails if action_confirm is called multiple times
        orders_to_check = self.filtered(lambda o: o.state not in ('sale', 'done'))
        
        # Check stock availability for all lines and send notifications
        for order in orders_to_check:
            order._ks_check_and_notify_stock_shortage_on_confirm()
        
        # Proceed with normal confirmation
        return super().action_confirm()
    
    def _ks_check_and_notify_stock_shortage_on_confirm(self):
        """Check stock availability for all order lines and send notifications.
        
        This method is called during Sale Order confirmation to:
        - Check all order lines for insufficient stock
        - Send email notifications to procurement team for each insufficient product
        - Post messages in chatter about stock shortages
        - Ensure no duplicate notifications are sent
        
        IMPORTANT: This method is ONLY called from action_confirm() when the order
        is being confirmed. Emails are NOT sent during draft/edit stages.
        """
        self.ensure_one()
        
        # Safety check: Only process draft/sent orders (not already confirmed)
        if self.state in ('sale', 'done', 'cancel'):
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
                        # Check if reserved quantity is less than required quantity
                        if move.product_uom_qty > move.reserved_availability:
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

