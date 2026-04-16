# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import ValidationError


class ProductProductCode(models.Model):
    """
    Uniqueness constraint on default_code at the variant level.

    The constraint is intentionally skipped when the context flag
    ``skip_sku_duplicate_check`` is True.  That flag is set by
    ProductTemplateInternalRef._generate_and_assign_sku() while it is
    writing all variant codes in one pass — the final cross-product check
    happens there instead, avoiding false positives caused by variants still
    holding their old codes during the update loop.
    """
    _inherit = 'product.product'

    @api.constrains('default_code')
    def _check_default_code_unique(self):
        # Suppressed during bulk regeneration to avoid race conditions.
        # _generate_and_assign_sku() performs its own post-write check.
        if self.env.context.get('skip_sku_duplicate_check'):
            return

        for rec in self:
            if not rec.default_code:
                continue

            duplicate = self.env['product.product'].with_context(
                active_test=False
            ).search(
                [
                    ('default_code', '=', rec.default_code),
                    ('id', '!=', rec.id),
                ],
                limit=1,
            )

            if duplicate:
                raise ValidationError(
                    _("Internal Reference '%(code)s' is already assigned to "
                      "'%(other)s'.\n"
                      "Each product variant must have a unique internal reference.")
                    % {
                        'code': rec.default_code,
                        'other': duplicate.display_name,
                    }
                )

    def write(self, vals):
        """
        Regenerate codes when a variant's attribute values change.
        """
        res = super().write(vals)
        if 'product_template_attribute_value_ids' in vals:
            for tmpl in self.mapped('product_tmpl_id'):
                tmpl._generate_and_assign_sku()
        return res
