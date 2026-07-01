from odoo import models


class AmazonAccount(models.Model):
    _inherit = 'amazon.account'

    def _find_matching_product(
        self,
        internal_reference,
        default_xmlid,
        default_name,
        default_type,
        fallback=True,
    ):
        """Override to use sudo() when fetching Amazon default products.

        The product_multi_company module restricts product.product visibility
        by company_ids.  Amazon Sale / Amazon Shipping products are shared
        across all companies (company_ids should be empty), but if they were
        accidentally assigned a company we still need to read them.
        Using sudo() bypasses the ir.rule so the sync never raises AccessError.
        """
        self.ensure_one()

        # Search for the product by internal reference within the current company
        product = self.env['product.product'].sudo().search([
            *self.env['product.product']._check_company_domain(self.company_id),
            ('default_code', '=', internal_reference),
        ], limit=1)

        if not product and fallback:
            # Fallback to the module-defined default product (e.g. Amazon Sale)
            product = self.env.ref(
                'sale_amazon.%s' % default_xmlid, raise_if_not_found=False
            )
            if product:
                product = product.sudo()

        if not product and fallback:
            # Restore the default product if it was deleted
            product = self.env['product.product'].sudo()._restore_data_product(
                default_name, default_type, default_xmlid
            )

        return product
