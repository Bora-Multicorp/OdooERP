# -*- coding: utf-8 -*-

import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _ks_get_stock_location_for_company(self, company):
        """Get the main stock location for a company.
        
        Returns the stock location of the main warehouse for the given company.
        
        Args:
            company: res.company record
            
        Returns:
            stock.location record or False
        """
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', company.id)
        ], limit=1, order='id')
        if warehouse:
            return warehouse.lot_stock_id
        return False

    def _ks_check_product_availability(self, product, quantity, company):
        """Check if the requested quantity is available in stock.
        
        Checks the physically available quantity for the product in the 
        company's main warehouse stock location.
        
        Args:
            product: product.product record
            quantity: float, requested quantity
            company: res.company record
            
        Returns:
            tuple: (is_available, available_qty) - bool and float
        """
        if not product or not product.is_storable:
            # Non-storable products (services, etc.) don't need stock check
            return True, 0.0
        
        location = self._ks_get_stock_location_for_company(company)
        if not location:
            # If no warehouse/location found, don't block
            return True, 0.0
        
        # Get the available quantity using stock.quant's method
        available_qty = self.env['stock.quant']._get_available_quantity(
            product, location, allow_negative=False
        )
        
        # Check if available quantity is sufficient
        is_available = available_qty >= quantity
        
        return is_available, available_qty

    def _ks_check_product_availability_other_companies(self, product, quantity, exclude_company):
        """Check if the requested quantity is available in other companies.
        
        Checks the physically available quantity for the product in all companies
        except the excluded company.
        
        Args:
            product: product.product record
            quantity: float, requested quantity
            exclude_company: res.company record to exclude from check
            
        Returns:
            list: List of dicts with company name and available quantity
        """
        if not product or not product.is_storable:
            return []
        
        available_in_companies = []
        
        # Get all companies except the excluded one
        all_companies = self.env['res.company'].search([
            ('id', '!=', exclude_company.id)
        ])
        
        for company in all_companies:
            location = self._ks_get_stock_location_for_company(company)
            if location:
                available_qty = self.env['stock.quant']._get_available_quantity(
                    product, location, allow_negative=False
                )
                if available_qty >= quantity:
                    available_in_companies.append({
                        'company': company.name,
                        'available_qty': available_qty,
                    })
        
        return available_in_companies

    def _ks_send_procurement_notification(self, product, quantity, order, available_qty):
        """Send email notification to procurement team about insufficient stock.
        
        Sends an email to all users in the procurement team for the order's company.
        The email includes product details, quantities, order info, and a direct link.
        
        Args:
            product: product.product record
            quantity: float, requested quantity
            order: sale.order record
            available_qty: float, available quantity in stock
        """
        company = order.company_id
        procurement_team = company.ks_sale_procurement_team_user_ids
        
        if not procurement_team:
            _logger.info(
                "KS Sale Order: No procurement team configured for company '%s'. "
                "Skipping stock notification email for order '%s'.",
                company.name, order.name or 'Draft'
            )
            return
        
        # Get the email template
        template = self.env.ref(
            'ks_sale_order.email_template_ks_stock_insufficient_notification',
            raise_if_not_found=False
        )
        
        if not template:
            _logger.warning(
                "KS Sale Order: Email template 'ks_sale_order.email_template_ks_stock_insufficient_notification' "
                "not found. Cannot send stock notification email."
            )
            return
        
        # Get the base URL for the order link
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        order_url = f"{base_url}/web#id={order.id}&model=sale.order&view_type=form"
        
        # Collect recipient emails from procurement team
        recipient_emails = ','.join(
            user.email for user in procurement_team if user.email
        )
        
        if not recipient_emails:
            _logger.warning(
                "KS Sale Order: Procurement team users have no email addresses configured. "
                "Cannot send stock notification email for order '%s'.",
                order.name or 'Draft'
            )
            return
        
        try:
            # Check if product is available in other companies
            other_companies = self._ks_check_product_availability_other_companies(
                product, quantity, company
            )
            
            # Prepare alternate company information for email
            alternate_company_info = None
            if other_companies:
                # Get the first available company (or all if multiple)
                company_names = [c['company'] for c in other_companies]
                if len(company_names) == 1:
                    alternate_company_info = company_names[0]
                else:
                    # Multiple companies: format as "Company1, Company2, and Company3"
                    if len(company_names) == 2:
                        alternate_company_info = f"{company_names[0]} and {company_names[1]}"
                    else:
                        alternate_company_info = f"{', '.join(company_names[:-1])}, and {company_names[-1]}"
            
            # Prepare context values for the email template
            template_ctx = template.with_context(
                product_name=product.display_name,
                requested_qty=quantity,
                available_qty=available_qty,
                order_name=order.name or 'Draft',
                company_name=company.name,
                order_url=order_url,
                alternate_company_name=alternate_company_info,
                has_alternate_company=bool(alternate_company_info),
            )
            
            # Send the email
            template_ctx.send_mail(
                order.id,
                force_send=True,
                email_values={
                    'email_to': recipient_emails,
                }
            )
            
            _logger.info(
                "KS Sale Order: Stock notification email sent to %s for order '%s' "
                "(Product: %s, Requested: %s, Available: %s)",
                recipient_emails, order.name or 'Draft', 
                product.display_name, quantity, available_qty
            )
        except Exception as e:
            _logger.error(
                "KS Sale Order: Failed to send stock notification email for order '%s': %s",
                order.name or 'Draft', str(e)
            )

    def _ks_check_and_notify_stock_availability(self, product_id, quantity, order):
        """Check stock availability and send notification if insufficient.
        
        This method does NOT block the operation, it only sends notification.
        
        Args:
            product_id: int, product.product id
            quantity: float, requested quantity
            order: sale.order record
        """
        if not product_id or not quantity or quantity <= 0:
            return
        
        product = self.env['product.product'].browse(product_id)
        company = order.company_id
        
        is_available, available_qty = self._ks_check_product_availability(
            product, quantity, company
        )
        
        if not is_available:
            # Send notification to procurement team (non-blocking)
            self._ks_send_procurement_notification(product, quantity, order, available_qty)
            
            # Check if available in other companies and post message
            if order and order.id:
                other_companies = self._ks_check_product_availability_other_companies(
                    product, quantity, company
                )
                
                if other_companies:
                    company_names = ', '.join([c['company'] for c in other_companies])
                    other_companies_msg = _(
                        "Note: %(product)s is available in other company(ies): %(companies)s\n"
                        "However, stock must be available in %(current_company)s to confirm this order.",
                        product=product.display_name,
                        companies=company_names,
                        current_company=company.name
                    )
                    
                    # Post message in order history (chatter)
                    # Use sudo to ensure message can be posted even if order is not fully saved
                    try:
                        order.sudo().message_post(
                            body=other_companies_msg,
                            message_type='notification',
                            subtype_xmlid='mail.mt_note',
                        )
                    except Exception as e:
                        _logger.warning(
                            "KS Sale Order: Failed to post other companies message for order %s: %s",
                            order.name or 'Draft', str(e)
                        )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to check stock and send notification if insufficient.
        
        This does NOT block creation - it only sends email notification to procurement team.
        """
        lines = super().create(vals_list)
        
        # Check stock availability and send notifications for each line
        for line in lines:
            # Skip display type lines (sections, notes)
            if line.display_type:
                continue
            
            if line.product_id and line.product_uom_qty and line.order_id:
                line._ks_check_and_notify_stock_availability(
                    line.product_id.id,
                    line.product_uom_qty,
                    line.order_id
                )
        
        return lines

    def write(self, values):
        """Override write to check stock and send notification when product/quantity changes.
        
        This does NOT block the update - it only sends email notification to procurement team.
        """
        result = super().write(values)
        
        product_id = values.get('product_id')
        quantity = values.get('product_uom_qty')
        
        # Only check if product or quantity was updated
        if product_id or quantity is not None:
            for line in self:
                # Skip display type lines (sections, notes)
                if line.display_type:
                    continue
                
                # Check if we need to send notification
                if line.product_id and line.product_uom_qty and line.order_id:
                    line._ks_check_and_notify_stock_availability(
                        line.product_id.id,
                        line.product_uom_qty,
                        line.order_id
                    )
        
        return result
