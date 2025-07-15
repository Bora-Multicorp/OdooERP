from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class ResPartner(models.Model):
    _inherit = 'res.partner'

    gst_status = fields.Selection([('active','Active'),('cancelled','Cancelled'),('suo_moto','Suo Moto'),('suspended','Suspended')], default="active")
    pan_blocked = fields.Boolean(
        string="Blocked by PAN",
        compute="_compute_pan_blocked",
        store=True,
        readonly=True
    )

    @api.depends('gst_status', 'l10n_in_pan')
    def _compute_pan_blocked(self):
        for partner in self:
            if not partner.l10n_in_pan:
                partner.pan_blocked = False
                continue

            related_partners = self.search([
                ('l10n_in_pan', '=', partner.l10n_in_pan)
            ])

            if any(p.gst_status in ['cancelled', 'suo_moto', 'suspended'] for p in related_partners):
                partner.pan_blocked = True
            else:
                partner.pan_blocked = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            pan = vals.get('l10n_in_pan')
            if pan:
                existing = self.env['res.partner'].sudo().search([
                    ('l10n_in_pan', '=', pan),
                    ('gst_status', 'in', ['cancelled', 'suo_moto', 'suspended'])
                ], limit=1)
                if existing:
                    raise ValidationError(_(
                        "Cannot create vendor. PAN %s is blocked due to GST status: %s") % (
                                              pan, existing.gst_status))
        return super().create(vals_list)

    def write(self, vals):
        # Store PANs and current GST statuses
        pan_map = {
            partner.l10n_in_pan: partner.gst_status
            for partner in self if partner.l10n_in_pan
        }

        res = super().write(vals)

        # Only act if gst_status actually changed
        if 'gst_status' in vals:
            new_status = vals['gst_status']
            for pan in pan_map:
                related_partners = self.env['res.partner'].sudo().search([
                    ('l10n_in_pan', '=', pan),
                    ('id', 'not in', self.ids)
                ])

                # Only update partners that have different gst_status
                to_update = related_partners.filtered(lambda p: p.gst_status != new_status)
                if to_update:
                    to_update.write({'gst_status': new_status})

        return res











