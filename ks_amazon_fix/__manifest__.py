{
    'name': 'KS Amazon Fix - Multi-Company Product Access',
    'version': '18.0.1.0.0',
    'summary': 'Fixes AccessError for Amazon Sale/Shipping products in multi-company setup',
    'description': """
        When product_multi_company is installed, it modifies the product.product_comp_rule
        so that products are only visible to companies listed in their company_ids field.
        Odoo's sale_amazon module creates "Amazon Sale" and "Amazon Shipping" products with
        no company set, but post_init_hook may populate company_ids.
        This module:
        - Clears company_ids on Amazon Sale and Amazon Shipping products (post_init_hook)
        - Patches account.move (sync) to use sudo() when reading Amazon products
        - Ensures new Amazon Sale/Shipping products created in future remain company-agnostic
    """,
    'author': 'KS',
    'category': 'Sales/Amazon',
    'license': 'LGPL-3',
    'depends': ['sale_amazon', 'product_multi_company'],
    'data': [
        'data/ir_rule.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'auto_install': False,
    'installable': True,
}
