
{
    "name": "Custom Contact Access Rights",
    "version": "0.1",
    "category": "Uncategorized",
    "author": "",
    "website": "",
    "license": "AGPL-3",
    'depends': ['l10n_in','contacts','purchase','sale'],
    "data": [
             "security/security.xml",
             "security/ir.model.access.csv",
             "views/custom_pan_block.xml",
             "views/custom_purchase.xml",
             "views/custom_sale.xml"],
    "installable": True,
}
