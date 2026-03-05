# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Zone Field
    ks_zone = fields.Selection([
        ('russia', 'Russia'),
        ('india', 'India'),
        ('dubai', 'Dubai'),
        ('sez', 'Sez'),
    ], string='Zone', required=True, default='india',
       help='Select the zone for this sale order. Automatic emails will only be sent for India and Dubai zones. This field cannot be changed once the order is confirmed.',
       tracking=True)

    # When True, no tax is allowed on order lines; confirm will raise if any line has tax
    ks_no_tax_allowed = fields.Boolean(
        string='No Tax',
        default=False,
        help='If checked, validation will prevent confirmation when any order line has tax applied.',
        tracking=True,
    )
    
    def write(self, vals):
        """Override write to prevent updating ks_zone when order is confirmed"""
        if 'ks_zone' in vals:
            for order in self:
                if order.state in ('sale', 'done'):
                    raise UserError(_('Zone cannot be changed once the sale order is confirmed.'))
        return super().write(vals)

    # Email Recipient Fields
    ks_email_recipient_ids = fields.Many2many(
        'res.partner',
        'sale_order_email_recipient_rel',
        'sale_order_id',
        'partner_id',
        string='Email Recipients',
        help='Main recipients who will receive automatic emails. Followers are excluded by default.',
    )
    ks_email_cc_ids = fields.Many2many(
        'res.partner',
        'sale_order_email_cc_rel',
        'sale_order_id',
        'partner_id',
        string='CC Recipients',
        help='Additional recipients to include in CC (can include followers if manually selected).',
    )
    
    # Email Status Fields
    ks_email_confirmed_sent = fields.Boolean(
        string='Confirmation Email Sent',
        default=False,
        copy=False,
        help='Indicates if confirmation email has been sent',
    )
    ks_email_packed_sent = fields.Boolean(
        string='Packed Email Sent',
        default=False,
        copy=False,
        help='Indicates if packed email has been sent',
    )
    ks_email_shipped_sent = fields.Boolean(
        string='Shipped Email Sent',
        default=False,
        copy=False,
        help='Indicates if shipped email has been sent',
    )
    
    # Global Configuration Reference
    ks_automail_config_id = fields.Many2one(
        'ks.automail.config',
        string='Email Configuration',
        compute='_compute_ks_automail_config_id',
        store=False,
        readonly=True,
        help='Global email configuration for this order (based on zone and company)',
    )
    
    # Auto-send Settings (can override global config)
    ks_auto_send_confirmation = fields.Boolean(
        string='Auto Send Confirmation Email',
        compute='_compute_auto_send_settings',
        store=True,
        readonly=False,
        help='Automatically send email when order is confirmed. Uses global config if not set.',
    )
    ks_auto_send_packed = fields.Boolean(
        string='Auto Send Packed Email',
        compute='_compute_auto_send_settings',
        store=True,
        readonly=False,
        help='Automatically send email when order is packed. Uses global config if not set.',
    )
    ks_auto_send_shipped = fields.Boolean(
        string='Auto Send Shipped Email',
        compute='_compute_auto_send_settings',
        store=True,
        readonly=False,
        help='Automatically send email when order is shipped. Uses global config if not set.',
    )
    
    @api.depends('ks_zone', 'company_id')
    def _compute_ks_automail_config_id(self):
        """Get the global configuration for this order's zone and company"""
        for order in self:
            if order.ks_zone in ['india', 'dubai']:
                config = self.env['ks.automail.config'].get_config_for_order(
                    order.ks_zone,
                    order.company_id.id if order.company_id else None
                )
                order.ks_automail_config_id = config.id if config else False
            else:
                # Russia, Sez: no auto email config
                order.ks_automail_config_id = False
    
    @api.depends('ks_automail_config_id', 'ks_zone')
    def _compute_auto_send_settings(self):
        """Compute auto-send settings from global config"""
        for order in self:
            if order.ks_automail_config_id:
                # Use global config defaults
                order.ks_auto_send_confirmation = order.ks_automail_config_id.auto_send_confirmation
                order.ks_auto_send_packed = order.ks_automail_config_id.auto_send_packed
                order.ks_auto_send_shipped = order.ks_automail_config_id.auto_send_shipped
            else:
                # No config or Russia zone - default to False
                if order.ks_zone in ('russia', 'sez'):
                    order.ks_auto_send_confirmation = False
                    order.ks_auto_send_packed = False
                    order.ks_auto_send_shipped = False
                else:
                    # Default to True for India/Dubai if no config
                    order.ks_auto_send_confirmation = True
                    order.ks_auto_send_packed = True
                    order.ks_auto_send_shipped = True

    def action_confirm(self):
        """Validate no tax when flag set; then send confirmation email"""
        for order in self:
            if order.ks_no_tax_allowed:
                lines_with_tax = order.order_line.filtered(
                    lambda l: not l.display_type and l.tax_id
                )
                if lines_with_tax:
                    raise ValidationError(_(
                        'Tax is not allowed on this order (No Tax is checked). '
                        'Please remove tax from the following line(s): %s'
                    ) % ', '.join(lines_with_tax.mapped('name') or lines_with_tax.mapped('product_id.name')))
        result = super().action_confirm()
        
        for order in self:
            # Only send emails for India and Dubai zones
            if order.ks_zone in ['india', 'dubai']:
                # Get auto-send setting (from config or manual override)
                auto_send = order.ks_auto_send_confirmation
                if auto_send and not order.ks_email_confirmed_sent:
                    order._send_confirmation_email()
        
        return result

    def _get_email_recipients(self):
        """Get email recipients from order or global config
        
        Returns:
            tuple: (email_to list, email_cc list)
        """
        self.ensure_one()
        
        # Priority: Order-specific recipients > Global config recipients > Customer
        recipients = self.ks_email_recipient_ids
        cc_recipients = self.ks_email_cc_ids
        
        if not recipients and self.ks_automail_config_id:
            recipients = self.ks_automail_config_id.default_recipient_ids
        
        if not cc_recipients and self.ks_automail_config_id:
            cc_recipients = self.ks_automail_config_id.default_cc_ids
        
        # Final fallback: customer
        if not recipients and self.partner_id.email:
            recipients = self.partner_id
        
        email_to = recipients.filtered(lambda p: p.email).mapped('email') if recipients else []
        email_cc = cc_recipients.filtered(lambda p: p.email).mapped('email') if cc_recipients else []
        
        return email_to, email_cc
    
    def _send_confirmation_email(self):
        """Send email when order is confirmed"""
        self.ensure_one()
        
        # Get template from global config or fallback to default
        template = None
        if self.ks_automail_config_id and self.ks_automail_config_id.email_template_confirmation_id:
            template = self.ks_automail_config_id.email_template_confirmation_id
        else:
            template = self.env.ref('ks_automail.email_template_sale_confirmation', raise_if_not_found=False)
        
        if not template:
            return
        
        # Get recipients
        email_to_list, email_cc_list = self._get_email_recipients()
        email_to = ','.join(email_to_list) if email_to_list else ''
        email_cc = ','.join(email_cc_list) if email_cc_list else False
        
        if not email_to:
            return  # No valid email addresses
        
        # Render email template fields
        # Subject uses Jinja2 syntax ({{ }}) - use inline_template engine
        subject = template._render_template(template.subject, self._name, [self.id], engine='inline_template')[self.id]
        # Body uses QWeb syntax - use qweb engine
        body_html = template._render_template(template.body_html, self._name, [self.id], engine='qweb')[self.id]
        
        # Get sender email (config > template > company > user)
        email_from = None
        if self.ks_automail_config_id and self.ks_automail_config_id.email_from:
            email_from = self.ks_automail_config_id.email_from
        else:
            # email_from uses Jinja2 syntax - use inline_template engine
            email_from = template._render_template(template.email_from, self._name, [self.id], engine='inline_template')[self.id]
        
        if not email_from:
            email_from = self.company_id.email_formatted if self.company_id else self.env.user.email_formatted
        
        # Create mail.mail record directly to avoid auto-subscription
        mail = self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body_html,
            'email_from': email_from,
            'email_to': email_to,
            'email_cc': email_cc,
            'model': self._name,
            'res_id': self.id,
            'auto_delete': False,
            'mail_message_id': False,  # Don't link to message to avoid subscription
        })
        
        # Send the email
        mail.send()
        
        # Mark as sent
        self.ks_email_confirmed_sent = True
        
        # Log in chatter without subscribing anyone
        recipient_names = [p.name for p in self.ks_email_recipient_ids] if self.ks_email_recipient_ids else email_to_list
        self.with_context(mail_create_nosubscribe=True).message_post(
            body=_('Confirmation email sent to: %s') % ', '.join(recipient_names),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
            partner_ids=[],
            mail_auto_delete=False,
        )

    def _send_packed_email(self):
        """Send email when order is packed"""
        self.ensure_one()
        
        # Get template from global config or fallback to default
        template = None
        if self.ks_automail_config_id and self.ks_automail_config_id.email_template_packed_id:
            template = self.ks_automail_config_id.email_template_packed_id
        else:
            template = self.env.ref('ks_automail.email_template_sale_packed', raise_if_not_found=False)
        
        if not template:
            return
        
        # Get recipients
        email_to_list, email_cc_list = self._get_email_recipients()
        email_to = ','.join(email_to_list) if email_to_list else ''
        email_cc = ','.join(email_cc_list) if email_cc_list else False
        
        if not email_to:
            return
        
        # Render email template fields
        # Subject uses Jinja2 syntax ({{ }}) - use inline_template engine
        subject = template._render_template(template.subject, self._name, [self.id], engine='inline_template')[self.id]
        # Body uses QWeb syntax - use qweb engine
        body_html = template._render_template(template.body_html, self._name, [self.id], engine='qweb')[self.id]
        
        # Get sender email (config > template > company > user)
        email_from = None
        if self.ks_automail_config_id and self.ks_automail_config_id.email_from:
            email_from = self.ks_automail_config_id.email_from
        else:
            # email_from uses Jinja2 syntax - use inline_template engine
            email_from = template._render_template(template.email_from, self._name, [self.id], engine='inline_template')[self.id]
        
        if not email_from:
            email_from = self.company_id.email_formatted if self.company_id else self.env.user.email_formatted
        
        mail = self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body_html,
            'email_from': email_from,
            'email_to': email_to,
            'email_cc': email_cc,
            'model': self._name,
            'res_id': self.id,
            'auto_delete': False,
            'mail_message_id': False,
        })
        
        mail.send()
        self.ks_email_packed_sent = True
        
        recipient_names = [p.name for p in self.ks_email_recipient_ids] if self.ks_email_recipient_ids else email_to_list
        self.with_context(mail_create_nosubscribe=True).message_post(
            body=_('Packed email sent to: %s') % ', '.join(recipient_names),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
            partner_ids=[],
            mail_auto_delete=False,
        )

    def _send_shipped_email(self):
        """Send email when order is shipped"""
        self.ensure_one()
        
        # Get template from global config or fallback to default
        template = None
        if self.ks_automail_config_id and self.ks_automail_config_id.email_template_shipped_id:
            template = self.ks_automail_config_id.email_template_shipped_id
        else:
            template = self.env.ref('ks_automail.email_template_sale_shipped', raise_if_not_found=False)
        
        if not template:
            return
        
        # Get recipients
        email_to_list, email_cc_list = self._get_email_recipients()
        email_to = ','.join(email_to_list) if email_to_list else ''
        email_cc = ','.join(email_cc_list) if email_cc_list else False
        
        if not email_to:
            return
        
        # Render email template fields
        # Subject uses Jinja2 syntax ({{ }}) - use inline_template engine
        subject = template._render_template(template.subject, self._name, [self.id], engine='inline_template')[self.id]
        # Body uses QWeb syntax - use qweb engine
        body_html = template._render_template(template.body_html, self._name, [self.id], engine='qweb')[self.id]
        
        # Get sender email (config > template > company > user)
        email_from = None
        if self.ks_automail_config_id and self.ks_automail_config_id.email_from:
            email_from = self.ks_automail_config_id.email_from
        else:
            # email_from uses Jinja2 syntax - use inline_template engine
            email_from = template._render_template(template.email_from, self._name, [self.id], engine='inline_template')[self.id]
        
        if not email_from:
            email_from = self.company_id.email_formatted if self.company_id else self.env.user.email_formatted
        
        mail = self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body_html,
            'email_from': email_from,
            'email_to': email_to,
            'email_cc': email_cc,
            'model': self._name,
            'res_id': self.id,
            'auto_delete': False,
            'mail_message_id': False,
        })
        
        mail.send()
        self.ks_email_shipped_sent = True
        
        recipient_names = [p.name for p in self.ks_email_recipient_ids] if self.ks_email_recipient_ids else email_to_list
        self.with_context(mail_create_nosubscribe=True).message_post(
            body=_('Shipped email sent to: %s') % ', '.join(recipient_names),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
            partner_ids=[],
            mail_auto_delete=False,
        )

    def action_send_manual_email(self, email_type='confirmation'):
        """Manual action to send emails"""
        self.ensure_one()
        
        # Get email_type from context if not passed
        if not email_type:
            email_type = self.env.context.get('email_type', 'confirmation')
        
        # Manual emails can be sent for any zone (including Russia)
        # Only automatic emails are restricted
        if email_type == 'confirmation':
            self._send_confirmation_email()
        elif email_type == 'packed':
            self._send_packed_email()
        elif email_type == 'shipped':
            self._send_shipped_email()
        else:
            raise UserError(_('Invalid email type'))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Email Sent'),
                'message': _('Email has been sent successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

