
{
    "name": "Custom Contact Access Rights",
    "version": "0.1",
    "category": "Uncategorized",
    "author": "Ksolves Private Limited",
    "website": "https://www.ksolves.com/",
    "license": "AGPL-3",
    'depends': ['l10n_in', 'contacts', 'purchase', 'sale', 'odx_m2m_attachment_preview'],
    "data": [
             "security/security.xml",
             "security/ir.model.access.csv",
             "views/custom_pan_block.xml",
             "views/custom_purchase.xml",
             "views/custom_sale.xml"],
    "installable": True,
}
