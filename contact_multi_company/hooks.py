import logging

_logger = logging.getLogger(__name__)

# Domain for the base res_partner_rule after enabling multi-company support.
# Preserves the partner_share exception (internal-user partners are always
# visible across companies) while replacing the single company_id filter with
# the many2many company_ids check.
_MULTI_COMPANY_DOMAIN = (
    "['|', '|', ('partner_share', '=', False),"
    " ('company_ids', '=', False),"
    " ('company_ids', 'in', company_ids)]"
)

# Original domain from Odoo base (restored on uninstall)
_ORIGINAL_DOMAIN = (
    "['|', '|', ('partner_share', '=', False),"
    " ('company_id', 'parent_of', company_ids),"
    " ('company_id', '=', False)]"
)


def post_init_hook(env):
    """Update the base partner record rule and migrate existing company_id values."""
    rule = env.ref("base.res_partner_rule", raise_if_not_found=False)
    if rule:
        rule.write({"active": True, "domain_force": _MULTI_COMPANY_DOMAIN})
    else:
        _logger.warning("base.res_partner_rule not found; record rule not updated.")

    # Migrate existing company_id values into the new company_ids M2M table
    # so that partners already assigned to a company remain visible after install.
    model = env["res.partner"]
    table_name = model._fields["company_ids"].relation
    column1 = model._fields["company_ids"].column1
    column2 = model._fields["company_ids"].column2
    env.cr.execute(
        f"""
        INSERT INTO {table_name} ({column1}, {column2})
        SELECT id, company_id
        FROM {model._table}
        WHERE company_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )


def uninstall_hook(env):
    """Restore the base partner record rule to its original single-company domain."""
    rule = env.ref("base.res_partner_rule", raise_if_not_found=False)
    if rule:
        rule.write({"domain_force": _ORIGINAL_DOMAIN})
