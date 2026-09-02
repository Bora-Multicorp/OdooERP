/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { patch } from '@web/core/utils/patch';
import { saleOrderLineProductField } from '@sale/js/sale_product_field';
import { ProductConfiguratorDialog } from '@sale/js/product_configurator_dialog/product_configurator_dialog';

async function checkAndSelectDirectVariant(orm, lineRecord, productTemplateId, displayName, edit) {
    if (edit || !displayName || !productTemplateId) {
        return false;
    }

    const cleanName = String(displayName).trim();

    // 1. Try extracting bracketed code tags (e.g. "[VAR-123] Shirt")
    const matches = cleanName.match(/\[(.*?)\]/g);
    if (matches && matches.length > 0) {
        for (const matchStr of matches) {
            const defaultCode = matchStr.replace(/^\[|\]$/g, '').trim();
            if (defaultCode) {
                const products = await orm.searchRead(
                    'product.product',
                    [
                        ['product_tmpl_id', '=', productTemplateId],
                        '|',
                        ['default_code', '=ilike', defaultCode],
                        ['barcode', '=ilike', defaultCode]
                    ],
                    ['id', 'display_name'],
                    { limit: 1 }
                );
                if (products && products.length > 0) {
                    const variant = products[0];
                    await lineRecord._update({
                        product_id: [variant.id, variant.display_name],
                    });
                    return true;
                }
            }
        }
    }

    // 2. Fallback: Search all variants for this template to see if displayName matches a specific variant
    const variants = await orm.searchRead(
        'product.product',
        [['product_tmpl_id', '=', productTemplateId]],
        ['id', 'display_name', 'default_code', 'barcode'],
        { limit: 100 }
    );

    if (variants && variants.length > 0) {
        const target = cleanName.toLowerCase();
        const matchedVariant = variants.find(v => {
            const code = (v.default_code || '').trim().toLowerCase();
            const barcode = (v.barcode || '').trim().toLowerCase();
            const disp = (v.display_name || '').trim().toLowerCase();

            if (code && (target === code || target.startsWith(`[${code}]`) || target.includes(code))) {
                return true;
            }
            if (barcode && (target === barcode || target.includes(barcode))) {
                return true;
            }
            if (disp && target === disp) {
                return true;
            }
            return false;
        });

        if (matchedVariant) {
            await lineRecord._update({
                product_id: [matchedVariant.id, matchedVariant.display_name],
            });
            return true;
        }
    }

    return false;
}

// Patch SaleOrderLineProductField component so SO lines bypass product picker dialog when selected by internal reference
patch(saleOrderLineProductField.component.prototype, {
    setup() {
        super.setup();
        this.orm = useService('orm');
    },

    async update(value) {
        const rawDisplayName = Array.isArray(value) ? value[1] : (value?.display_name || value?.label || '');
        this.lastSelectedDisplayName = rawDisplayName;
        return super.update(value);
    },

    async _openProductConfigurator(edit = false) {
        const lineRecord = this.props.record;
        const lineData = lineRecord.data;

        const productTemplateId = Array.isArray(lineData.product_template_id)
            ? lineData.product_template_id[0]
            : (lineData.product_template_id?.id || lineData.product_template_id || false);

        const displayName = this.lastSelectedDisplayName || (Array.isArray(lineData.product_template_id)
            ? lineData.product_template_id[1]
            : (lineData.product_template_id?.display_name || ''));

        this.lastSelectedDisplayName = null;

        const selectedVariant = await checkAndSelectDirectVariant(this.orm, lineRecord, productTemplateId, displayName, edit);
        if (selectedVariant) {
            return;
        }

        return super._openProductConfigurator(edit);
    },
});

export class PurchaseOrderLineProductField extends saleOrderLineProductField.component {
    static template = 'purchase.PurchaseProductField';

    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.orm = useService('orm');
    }

    get configurationButtonHelp() {
        return 'Edit Configuration';
    }

    _getVariantPtavIds(lineData) {
        const ptavs = lineData.product_template_attribute_value_ids;
        if (!ptavs) {
            return [];
        }
        if (Array.isArray(ptavs)) {
            return ptavs;
        }
        if (ptavs.records) {
            return ptavs.records.map(r => r.data.id || r.resId);
        }
        if (ptavs.currentIds) {
            return ptavs.currentIds;
        }
        return [];
    }

    _getNoVariantPtavIds(lineData) {
        const ptavs = lineData.product_no_variant_attribute_value_ids;
        if (!ptavs) {
            return [];
        }
        if (Array.isArray(ptavs)) {
            return ptavs;
        }
        if (ptavs.records) {
            return ptavs.records.map(r => r.data.id || r.resId);
        }
        if (ptavs.currentIds) {
            return ptavs.currentIds;
        }
        return [];
    }

    async _getCustomPtavs(lineData) {
        const customValues = lineData.product_custom_attribute_value_ids;
        if (!customValues || !customValues.records) {
            return [];
        }
        return customValues.records.map(rec => ({
            ptav_id: Array.isArray(rec.data.custom_product_template_attribute_value_id)
                ? rec.data.custom_product_template_attribute_value_id[0]
                : rec.data.custom_product_template_attribute_value_id,
            value: rec.data.custom_value,
        }));
    }

    async update(value) {
        const rawDisplayName = Array.isArray(value) ? value[1] : (value?.display_name || value?.label || '');
        this.lastSelectedDisplayName = rawDisplayName;
        return super.update(value);
    }

    async _openProductConfigurator(edit = false) {
        const purchaseOrderRecord = this.props.record.model.root;
        const purchaseOrderLine = this.props.record.data;

        const productTemplateId = Array.isArray(purchaseOrderLine.product_template_id)
            ? purchaseOrderLine.product_template_id[0]
            : (purchaseOrderLine.product_template_id?.id || purchaseOrderLine.product_template_id || false);

        const displayName = this.lastSelectedDisplayName || (Array.isArray(purchaseOrderLine.product_template_id)
            ? purchaseOrderLine.product_template_id[1]
            : (purchaseOrderLine.product_template_id?.display_name || ''));

        this.lastSelectedDisplayName = null;

        const selectedVariant = await checkAndSelectDirectVariant(this.orm, this.props.record, productTemplateId, displayName, edit);
        if (selectedVariant) {
            return;
        }

        let ptavIds = this._getVariantPtavIds(purchaseOrderLine);
        let customPtavs = [];

        if (edit) {
            ptavIds.push(...this._getNoVariantPtavIds(purchaseOrderLine));
            customPtavs = await this._getCustomPtavs(purchaseOrderLine);
        }

        const productUOMId = Array.isArray(purchaseOrderLine.product_uom)
            ? purchaseOrderLine.product_uom[0]
            : (purchaseOrderLine.product_uom?.id || purchaseOrderLine.product_uom || 0);

        const companyId = Array.isArray(purchaseOrderRecord.data.company_id)
            ? purchaseOrderRecord.data.company_id[0]
            : (purchaseOrderRecord.data.company_id?.id || purchaseOrderRecord.data.company_id || 0);

        let rawPricelist = purchaseOrderRecord.data.pricelist_id;
        let pricelistId = 0;
        if (rawPricelist) {
            pricelistId = Array.isArray(rawPricelist) ? rawPricelist[0] : (rawPricelist.id || rawPricelist || 0);
        }
        pricelistId = Number(pricelistId) || 0;

        let rawCurrency = purchaseOrderLine.currency_id || purchaseOrderRecord.data.currency_id;
        let currencyId = 0;
        if (rawCurrency) {
            currencyId = Array.isArray(rawCurrency) ? rawCurrency[0] : (rawCurrency.id || rawCurrency || 0);
        }
        currencyId = Number(currencyId) || 0;

        const quantity = Number(purchaseOrderLine.product_qty || purchaseOrderLine.product_uom_qty || 1);

        let soDate = '';
        const rawDate = purchaseOrderRecord.data.date_order || purchaseOrderRecord.data.date_approve;
        if (rawDate) {
            if (typeof rawDate === 'string') {
                soDate = rawDate;
            } else if (typeof rawDate === 'object' && rawDate.toISODate) {
                soDate = rawDate.toISODate();
            } else if (typeof rawDate === 'object' && rawDate.toISO) {
                soDate = rawDate.toISO();
            } else {
                soDate = String(rawDate);
            }
        }
        if (!soDate) {
            soDate = new Date().toISOString().split('T')[0];
        }

        this.dialog.add(ProductConfiguratorDialog, {
            productTemplateId,
            ptavIds,
            customPtavs,
            quantity,
            productUOMId: Number(productUOMId) || 0,
            companyId: Number(companyId) || 0,
            pricelistId: Number(pricelistId) || 0,
            currencyId: Number(currencyId) || 0,
            soDate: String(soDate),
            edit,
            save: async (mainProduct, optionalProducts) => {
                const line = this.props.record;
                const qty = mainProduct.quantity || mainProduct.qty || 1;

                await line._update({
                    product_id: [mainProduct.id, mainProduct.display_name],
                });
                await line._update({
                    product_qty: qty,
                });

                if (optionalProducts && optionalProducts.length > 0) {
                    for (const product of optionalProducts) {
                        const optQty = product.quantity || product.qty || 1;
                        const newLine = await purchaseOrderRecord.data.order_line.addNewRecord({ position: 'bottom', mode: 'readonly' });
                        await newLine._update({
                            product_id: [product.id, product.display_name],
                        });
                        await newLine._update({
                            product_qty: optQty,
                        });
                    }
                }
                purchaseOrderRecord.data.order_line.leaveEditMode();
            },
            discard: () => {
                purchaseOrderRecord.data.order_line.delete(this.props.record);
            },
        });
    }
}

export const purchaseOrderLineProductField = {
    ...saleOrderLineProductField,
    component: PurchaseOrderLineProductField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = saleOrderLineProductField.extractProps(fieldInfo, dynamicInfo);
        props.readonlyField = dynamicInfo.readonly;
        return props;
    },
};

registry.category('fields').add('pol_product_many2one', purchaseOrderLineProductField);


