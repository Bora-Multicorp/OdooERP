# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    @api.model
    def _default_ks_zone(self):
        company = self.env.company
        # Indian company defaults to 'india'
        if company.country_id and company.country_id.code == 'IN':
            return 'india'
        # Overseas companies have no default (user chooses manually)
        return False

    ks_zone = fields.Selection([
            ('russia', 'Russia'),
            ('india', 'India'),
            ('dubai', 'Dubai'),
            ('sez', 'Sez'),
            ('dafza', 'DAFZA'),
            ('mainland', 'MainLand'),
            ('export', 'Export'),
            ('other', 'Other')], default=_default_ks_zone, string='Zone', required=True,
       help='Select the zone for this purchase order.',
       tracking=True)
    is_overseas_company = fields.Boolean(compute='_compute_is_overseas_company')
    ks_no_tax_allowed = fields.Boolean(
        string='No Tax',
        default=False,
        help='If checked, no tax can be applied on order lines; existing line taxes are cleared.',
        tracking=True,
    )
    
    @api.onchange('company_id')
    def _onchange_company_id_update_zone(self):
        """ Automatically clear/reset invalid values when changing companies """
        if self.company_id:
            is_overseas = self.company_id.country_id.code != 'IN' if self.company_id.country_id else False
            if is_overseas:
                if self.ks_zone in ['india', 'dubai', 'sez']:
                    self.ks_zone = False
            else:
                if self.ks_zone in ['dafza', 'mainland', 'export', 'other']:
                    self.ks_zone = 'india'

    @api.depends('company_id', 'company_id.country_id')
    def _compute_is_overseas_company(self):
        for rec in self:
            rec.is_overseas_company = bool(rec.company_id and rec.company_id.country_id.code != 'IN')

    @api.onchange('ks_no_tax_allowed')
    def _onchange_ks_no_tax_allowed_clear_tax(self):
        """When No Tax is ticked, remove tax from all order lines."""
        if self.ks_no_tax_allowed and self.order_line:
            for line in self.order_line:
                if line.taxes_id:
                    line.taxes_id = [(5, 0, 0)]

    def write(self, vals):
        """Clear line taxes when No Tax is set; prevent changing ks_zone once order is in purchase/done state."""
        if vals.get('ks_no_tax_allowed'):
            for order in self:
                lines_with_tax = order.order_line.filtered(lambda l: l.taxes_id)
                if lines_with_tax:
                    lines_with_tax.write({'taxes_id': [(5, 0, 0)]})
        if 'ks_zone' in vals:
            for order in self:
                if order.state in ('purchase', 'done'):
                    raise UserError(_('Zone cannot be changed once the purchase order is confirmed.'))
        return super().write(vals)

    def button_confirm(self):
        """Validate no tax when flag set before confirming"""
        for order in self:
            if order.ks_no_tax_allowed:
                lines_with_tax = order.order_line.filtered(
                    lambda l: l.taxes_id
                )
                if lines_with_tax:
                    raise ValidationError(_(
                        'Tax is not allowed on this order (No Tax is checked). '
                        'Please remove tax from the following line(s): %s'
                    ) % ', '.join(lines_with_tax.mapped('name') or lines_with_tax.mapped('product_id.name')))
        return super().button_confirm()

    def action_rfq_send(self):
        """Use our custom 'Purchase Order Sent to Vendor' template when sending a PO (not RFQ).
        Base template is in purchase/data with noupdate=1 so we cannot override it via XML."""
        self.ensure_one()
        if not self.env.context.get('send_rfq', False):
            # Sending Purchase Order: use our template
            template = self.env.ref(
                'ks_automail.email_template_purchase_order_sent_to_vendor',
                raise_if_not_found=False,
            )
            if template:
                ir_model_data = self.env['ir.model.data']
                try:
                    compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
                except ValueError:
                    compose_form_id = False
                ctx = dict(self.env.context or {})
                ctx.update({
                    'default_model': 'purchase.order',
                    'default_res_ids': self.ids,
                    'default_template_id': template.id,
                    'default_composition_mode': 'comment',
                    'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
                    'email_notification_allow_footer': True,
                    'force_email': True,
                    'mark_rfq_as_sent': True,
                })
                lang = self.env.context.get('lang')
                if template.lang and self.ids:
                    lang = template._render_lang(self.ids).get(self.id) or lang
                self = self.with_context(lang=lang)
                ctx['model_description'] = _('Purchase Order')
                return {
                    'name': _('Compose Email'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'mail.compose.message',
                    'views': [(compose_form_id, 'form')],
                    'view_id': compose_form_id,
                    'target': 'new',
                    'context': ctx,
                }
        return super().action_rfq_send()
