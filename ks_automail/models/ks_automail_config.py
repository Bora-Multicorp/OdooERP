# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KsAutomailConfig(models.Model):
    """Global configuration for automatic email notifications per zone/company"""
    _name = 'ks.automail.config'
    _description = 'KS Auto Mail Configuration'
    _order = 'zone, company_id'

    name = fields.Char(
        string='Configuration Name',
        required=True,
        help='A descriptive name for this configuration (e.g., "India Email Config")',
    )
    zone = fields.Selection([
        ('india', 'India'),
        ('dubai', 'Dubai'),
    ], string='Zone', required=True,
       help='Zone for which this configuration applies')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        help='Leave empty for global configuration, or specify a company for company-specific settings',
    )
    
    # Email Templates
    email_template_confirmation_id = fields.Many2one(
        'mail.template',
        string='Confirmation Email Template',
        domain="[('model', '=', 'sale.order')]",
        required=True,
        help='Email template to use when order is confirmed',
    )
    email_template_packed_id = fields.Many2one(
        'mail.template',
        string='Packed Email Template',
        domain="[('model', '=', 'sale.order')]",
        required=True,
        help='Email template to use when order is packed',
    )
    email_template_shipped_id = fields.Many2one(
        'mail.template',
        string='Shipped Email Template',
        domain="[('model', '=', 'sale.order')]",
        required=True,
        help='Email template to use when order is shipped',
    )
    
    # Sender Email
    email_from = fields.Char(
        string='Sender Email',
        help='Email address to use as sender. Leave empty to use template default or company email.',
    )
    
    # Default Recipients
    default_recipient_ids = fields.Many2many(
        'res.partner',
        'ks_automail_config_recipient_rel',
        'config_id',
        'partner_id',
        string='Default Email Recipients',
        help='Default recipients who will receive automatic emails. Can be overridden per Sale Order.',
    )
    default_cc_ids = fields.Many2many(
        'res.partner',
        'ks_automail_config_cc_rel',
        'config_id',
        'partner_id',
        string='Default CC Recipients',
        help='Default CC recipients. Can be overridden per Sale Order.',
    )
    
    # Auto-send Settings
    auto_send_confirmation = fields.Boolean(
        string='Auto Send Confirmation Email',
        default=True,
        help='Automatically send email when order is confirmed',
    )
    auto_send_packed = fields.Boolean(
        string='Auto Send Packed Email',
        default=True,
        help='Automatically send email when order is packed',
    )
    auto_send_shipped = fields.Boolean(
        string='Auto Send Shipped Email',
        default=True,
        help='Automatically send email when order is shipped',
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to disable this configuration without deleting it',
    )
    
    @api.constrains('zone', 'company_id')
    def _check_unique_config(self):
        """Ensure only one active configuration per zone/company combination"""
        for config in self:
            if config.active:
                domain = [
                    ('zone', '=', config.zone),
                    ('company_id', '=', config.company_id.id),
                    ('active', '=', True),
                    ('id', '!=', config.id),
                ]
                existing = self.search(domain, limit=1)
                if existing:
                    raise ValidationError(
                        _('An active configuration already exists for zone "%s" and company "%s". '
                          'Please deactivate the existing configuration or modify it instead.')
                        % (config.zone, config.company_id.name if config.company_id else _('Global'))
                    )
    
    def toggle_active(self):
        """Toggle active status"""
        for record in self:
            record.active = not record.active
    
    @api.model
    def get_config_for_order(self, zone, company_id=None):
        """Get the appropriate configuration for a Sale Order
        
        Priority:
        1. Company-specific config for the zone
        2. Global config for the zone (company_id is False)
        
        Args:
            zone: str, 'india' or 'dubai'
            company_id: int, optional company ID
            
        Returns:
            ks.automail.config record or empty recordset
        """
        if zone not in ['india', 'dubai']:
            return self.browse()
        
        # First try company-specific config
        if company_id:
            config = self.search([
                ('zone', '=', zone),
                ('company_id', '=', company_id),
                ('active', '=', True),
            ], limit=1)
            if config:
                return config
        
        # Fallback to global config (no company)
        config = self.search([
            ('zone', '=', zone),
            ('company_id', '=', False),
            ('active', '=', True),
        ], limit=1)
        
        return config

