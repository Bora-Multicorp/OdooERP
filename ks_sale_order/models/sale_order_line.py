# -*- coding: utf-8 -*-

import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _ks_get_stock_location_for_company(self, company, warehouse=None):
        """Get the stock location for a company.
        
        Returns the stock location of the specified warehouse or the main warehouse 
        for the given company. Ensures the location belongs to the specified company.
        
        Args:
            company: res.company record
            warehouse: stock.warehouse record (optional) - if provided, uses this warehouse
            
        Returns:
            stock.location record or False
        """
        if not company:
            return False
        
        # If warehouse is provided and belongs to the company, use it
        if warehouse and warehouse.company_id.id == company.id:
            location = warehouse.lot_stock_id
            if location:
                return location
        
        # Otherwise, search for warehouse with explicit company filter
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', company.id)
        ], limit=1, order='id')
        
        if not warehouse:
            return False
        
        location = warehouse.lot_stock_id
        
        # Double-check: Ensure location belongs to the same company
        # Locations should have company_id directly or inherit from warehouse
        location_company = location.company_id or (location.warehouse_id and location.warehouse_id.company_id)
        if location_company and location_company.id != company.id:
            # Location company doesn't match - this shouldn't happen but safeguard
            _logger.warning(
                "KS Sale Order: Location %s (ID: %s) company (%s) doesn't match requested company %s (ID: %s). "
                "Skipping stock check.",
                location.name, location.id, location_company.name, company.name, company.id
            )
            return False
        
        return location

    def _ks_check_product_availability(self, product, quantity, company, warehouse=None):
        """Check if the requested quantity is available in stock.
        
        Checks the physically available quantity for the product in the 
        company's warehouse stock location. This check is STRICTLY 
        company-specific and only considers stock in the specified company.
        
        Args:
            product: product.product record
            quantity: float, requested quantity
            company: res.company record (must match Sale Order's company)
            warehouse: stock.warehouse record (optional) - if provided, uses this warehouse's location
            
        Returns:
            tuple: (is_available, available_qty) - bool and float
        """
        if not product or not product.is_storable:
            # Non-storable products (services, etc.) don't need stock check
            return True, 0.0
        
        if not company:
            # No company specified - cannot check stock
            _logger.warning(
                "KS Sale Order: No company specified for stock check. Product: %s, Quantity: %s",
                product.display_name if product else 'Unknown', quantity
            )
            return True, 0.0
        
        # Get location for the SPECIFIC company only (use warehouse if provided)
        location = self._ks_get_stock_location_for_company(company, warehouse=warehouse)
        if not location:
            # If no warehouse/location found for this company, log and don't trigger alert
            _logger.info(
                "KS Sale Order: No warehouse/location found for company '%s' (ID: %s). "
                "Product: %s. Skipping stock check.",
                company.name, company.id, product.display_name if product else 'Unknown'
            )
            return True, 0.0
        
        # Get the available quantity using product's qty_available with warehouse context
        # This matches what the user sees in the UI ("On Hand") and includes child locations
        # The location is already company-specific (from warehouse with company_id filter)
        try:
            # Use with_company to ensure we're in the correct company context
            product_with_company = product.with_company(company.id)
            
            # Use warehouse context to get qty_available for the specific warehouse
            # This ensures we get stock in the warehouse's location and all its child locations
            # This matches what users see in the product form ("On Hand")
            if warehouse:
                # Use warehouse context to get stock for this specific warehouse
                product_with_warehouse = product_with_company.with_context(warehouse_id=warehouse.id)
            else:
                # No warehouse specified, use location context
                product_with_warehouse = product_with_company.with_context(location=location.id)
            
            # Get qty_available which includes child locations (matches UI "On Hand")
            # This is company-specific because we used with_company(company.id)
            # Force recomputation to ensure we get the latest stock value
            product_with_warehouse.invalidate_recordset(['qty_available'])
            available_qty = product_with_warehouse.qty_available
            
            _logger.info(
                "KS Sale Order: Stock check - Product: %s (ID: %s), Company: %s (ID: %s), "
                "Location: %s (ID: %s), Warehouse: %s, Requested: %s, Available (qty_available): %s",
                product.display_name, product.id, company.name, company.id,
                location.name, location.id,
                warehouse.name if warehouse else 'Default',
                quantity, available_qty
            )
        except Exception as e:
            _logger.error(
                "KS Sale Order: Error checking stock availability for product %s (ID: %s) "
                "in company %s (ID: %s), location %s (ID: %s): %s",
                product.display_name if product else 'Unknown',
                product.id if product else 'N/A',
                company.name, company.id,
                location.name if location else 'N/A',
                location.id if location else 'N/A',
                str(e)
            )
            # On error, don't trigger alert - assume available
            return True, 0.0
        
        # Check if available quantity is sufficient
        # Only consider it insufficient if available_qty is actually less than requested
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

    # NOTE: _ks_check_and_notify_stock_availability() method has been removed.
    # Stock shortage email notifications are now only sent during Sale Order confirmation
    # via sale_order.action_confirm() -> _ks_check_and_notify_stock_shortage_on_confirm()

    @api.model_create_multi
    def create(self, vals_list):
        """Override create - stock check removed.
        
        Stock validation has been moved to Sale Order confirmation step.
        Users can now freely add products without stock availability checks.
        """
        return super().create(vals_list)

    def write(self, values):
        """Override write - stock check removed.
        
        Stock validation has been moved to Sale Order confirmation step.
        Users can now freely modify products/quantities without stock availability checks.
        """
        return super().write(values)
