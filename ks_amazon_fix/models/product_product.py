import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _configure_for_amazon(self):
        """Extend to strip company restrictions from Amazon products."""
        super()._configure_for_amazon()
        tmpl_ids = self.sudo().mapped('product_tmpl_id').ids
        if tmpl_ids:
            self._clear_amazon_product_companies(tmpl_ids)

    @api.model
    def _clear_amazon_product_companies(self, tmpl_ids):
        """Remove all company restrictions from the given product_template IDs using SQL."""
        cr = self.env.cr

        # Get the actual Many2many relation table from the ORM field definition
        # This avoids hardcoding table names that differ per Odoo version/install.
        tmpl_field = self.env['product.template']._fields.get('company_ids')
        if tmpl_field and hasattr(tmpl_field, 'relation') and tmpl_field.relation:
            relation_table = tmpl_field.relation
            column1 = tmpl_field.column1  # FK to product_template
            _logger.info(
                'ks_amazon_fix: clearing company_ids via table=%s col=%s for tmpl_ids=%s',
                relation_table, column1, tmpl_ids,
            )
            cr.execute(
                f'DELETE FROM "{relation_table}" WHERE "{column1}" = ANY(%s)',  # noqa: S608
                [tmpl_ids]
            )
        else:
            _logger.warning('ks_amazon_fix: could not resolve company_ids relation table')

        # Clear company_id on the template (NULL = no restriction)
        cr.execute(
            'UPDATE product_template SET company_id = NULL WHERE id = ANY(%s)',
            [tmpl_ids]
        )
        _logger.info('ks_amazon_fix: cleared company restrictions for tmpl_ids=%s', tmpl_ids)
