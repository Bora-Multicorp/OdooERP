# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import ValidationError


class ProductProductCode(models.Model):
    """
    Adds a uniqueness constraint on default_code (Internal Reference) at the
    product variant (product.product) level.

    Odoo's base module does not enforce this at the DB level, so we enforce it
    via a Python constraint that is fired whenever default_code is written.

    The check intentionally includes archived (active=False) products to
    prevent silent reference conflicts when products are reactivated.
    """
    _inherit = 'product.product'

    @api.constrains('default_code')
    def _check_default_code_unique(self):
        """
        Raise ValidationError if any *other* product variant already uses
        the same internal reference.

        Notes
        -----
        • Empty / False codes are allowed (a product may have no ref).
        • active=False records are included in the search to catch conflicts
          with archived products.
        """
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
                      "product variant '%(product)s' (ID: %(pid)d).\n"
                      "Each product variant must have a unique internal "
                      "reference.")
                    % {
                        'code': rec.default_code,
                        'product': duplicate.display_name,
                        'pid': duplicate.id,
                    }
                )

    def write(self, vals):
        """
        Regenerate the internal reference when a variant's attribute values
        change (e.g. a colour or storage option is reassigned).

        Attribute value changes on a variant arrive as writes to
        ``product_template_attribute_value_ids``.  We detect this and ask
        the parent template to regenerate codes for all its variants.
        """
        res = super().write(vals)

        if 'product_template_attribute_value_ids' in vals:
            templates = self.mapped('product_tmpl_id')
            for tmpl in templates:
                tmpl._generate_and_assign_sku()

        return res
