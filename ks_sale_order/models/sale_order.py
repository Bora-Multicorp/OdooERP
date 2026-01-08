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
            
            # Check availability in same company
            is_available, available_qty = line._ks_check_product_availability(
                line.product_id, 
                line.product_uom_qty, 
                self.company_id
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
        """Override action_confirm to allow confirmation regardless of stock availability.
        
        Stock validation has been removed - Sale Orders can now be confirmed
        even if products have insufficient stock. All other workflows (delivery,
        invoicing, backorder, etc.) remain unchanged.
        """
        # Stock validation removed - allow confirmation regardless of stock
        return super().action_confirm()
    
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
                
                # Check availability
                is_available, available_qty = line._ks_check_product_availability(
                    line.product_id,
                    line.product_uom_qty,
                    order.company_id
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
            
            # Check availability
            is_available, available_qty = line._ks_check_product_availability(
                line.product_id,
                line.product_uom_qty,
                self.company_id
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
            
            # Check availability
            is_available, available_qty = line._ks_check_product_availability(
                line.product_id,
                line.product_uom_qty,
                self.company_id
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

