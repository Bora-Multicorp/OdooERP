# -*- coding: utf-8 -*-
{
    'name': "Bora Product Internal Reference",
    'summary': "Structured, fully auto-generated default_code for product variants",
    'description': """
        Replaces the generic SKU generator in ks_product_master with a
        structured, category-aware internal reference builder.

        No manual code configuration is required — every segment is derived
        automatically from the existing product data.

        Toner & Inks:    BRAND-TYPE-MODEL-COLOUR
        All others:      BRAND-CAT-(GRP)-MODEL-VARIANT-COLOUR

        Segment derivation (all automatic)
        -----------------------------------
        BRAND   → abbreviation of brand_id.name          (3 chars)
        CAT     → abbreviation of categ_id.name          (3 chars)
        GRP     → abbreviation of accessory_group.name   (3 chars, optional)
        MODEL   → first 6 alphanumeric chars of product name
        TYPE    → abbreviation of "Type" attribute value (3 chars, toner only)
        VARIANT → first 5 chars of concatenated other attribute values
        COLOUR  → abbreviation of "Colour/Color" attribute value (3 chars)

        Manual override: set part_code on the product to bypass auto-generation.
    """,
    'author': "Bora",
    'category': 'Inventory/Products',
    'version': '18.0.1.0.0',

    'depends': ['ks_product_master'],

    'data': [
        'views/product_template_views.xml',
    ],

    'installable': True,
    'application': False,
    'license': 'Other proprietary',
}
