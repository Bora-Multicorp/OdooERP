import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Clear company restrictions on Amazon Sale / Shipping products.

    Also removes the stale placeholder ir.rule that was created in earlier
    versions of this module (its domain blocked access instead of granting it).
    """
    # 1. Remove stale ir.rule if it exists (placeholder domain blocks access)
    stale_rule = env.ref(
        'ks_amazon_fix.rule_amazon_products_all_companies', raise_if_not_found=False
    )
    if stale_rule:
        stale_rule.sudo().unlink()
        _logger.info('ks_amazon_fix: removed stale ir.rule rule_amazon_products_all_companies')

    # 2. Collect product_template IDs for Amazon Sale / Amazon Shipping
    cr = env.cr
    cr.execute("""
        SELECT pp.id, pp.product_tmpl_id
          FROM product_product pp
          JOIN ir_model_data imd
            ON imd.res_id = pp.id
           AND imd.model  = 'product.product'
           AND imd.module = 'sale_amazon'
           AND imd.name  IN ('default_product', 'shipping_product')
    """)
    rows = cr.fetchall()
    if not rows:
        _logger.warning('ks_amazon_fix: Amazon products not found — skipping company clear')
        return

    tmpl_ids = [r[1] for r in rows]
    _logger.info('ks_amazon_fix: clearing company restrictions for tmpl_ids=%s', tmpl_ids)

    # 3. Clear company_ids / company_id via SQL (bypass ORM recomputes)
    env['product.product']._clear_amazon_product_companies(tmpl_ids)
