
import { getCurrency } from "@web/core/currency";
import { formatFloat, formatInteger } from "@web/views/fields/formatters";
import { localization } from "@web/core/l10n/localization";
import { eraseCookie } from "@ks_dashboard_ninja/js/cookies";
import { _t } from "@web/core/l10n/translation";
import { hexToRGBA, darkenColor } from "@web/core/colors/colors";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { isBinarySize } from "@web/core/utils/binary";
import { fileTypeMagicWordMap } from "@web/views/fields/image/image_field";
import { imageUrl } from "@web/core/utils/urls";
import { useComponent } from "@odoo/owl";


// TODO: Is it okay to use internal object - '__owl__' ??
// TODO: GridStack getGridItems can be used instead
// TODO: GridStack nodes can be used instead
export function DNUseRef() {
    const node = useComponent().__owl__;
    const refs = node.refs;
    return {
        getEl(name) {
            const el = refs[name];
            return el ? el : null;
        },
    };
}


export function standardDashboardItemProps(){
    return {
        itemId : {
            type: [Number, Boolean],
            validate: (id) => id > 0 || id === false,
        },
        isPreview: { type: Boolean, optional: true },   // Make Chart non clickable with no chart button options
        isFormPreview: { type: Boolean, optional: true },   // Use for functionalities in the form view
        dashboardData: { type: [Object, Boolean], optional: true },
        filtersConfig: { type: [Object, Boolean], optional: true },
        dateFilterConfig: { type: [Object, Boolean], optional: true },
        itemConfig: { type: [Object, Boolean], optional: true },
        isAIExplanation: { type: Boolean, optional: true },   // Flag for making  chart with explanation
        dnStore: { type: Object, optional: true },   // Flag for making  chart with explanation
        visibleItemSet: { type: Object, optional: true },
        basicData: { type: Object, optional: true },
    }
}

// todo: update below static props
export function standardDashboardItemDefaultProps(){
    return { isPreview: false, dashboardData: false, filtersConfig: false, dateFilterConfig: false, itemConfig: false }
}

export function dnIndianFormatter(num, precision_digits){
    const siValues = [1, 1E3, 1E5, 1E7, 1E9];
    const siSymbols = { 1: "", 1E3: "Th", 1E5: "Lakh", 1E7: "Cr", 1E9: "Arab" };

    const rx = /\.0+$|(\.[0-9]*[1-9])0+$/;
    const isNegative = num < 0;
    num = Math.abs(num);
    const value = siValues.findLast(v => num >= v) || 1;

    const formattedNum = (num / value).toFixed(precision_digits).replace(rx, "$1");

    return (isNegative ? "-" : "") + formattedNum + siSymbols[value];
}

export function dnEnglishFormatter(num, precision_digits) {
    const siValues = [1, 1E3, 1E6, 1E9, 1E12, 1E15, 1E18];
    const siSymbols = { 1: "", 1E3: "k", 1E6: "M", 1E9: "G", 1E12: "T", 1E15: "P", 1E18: "E"};

    const rx = /\.0+$|(\.[0-9]*[1-9])0+$/;
    const isNegative = num < 0;
    num = Math.abs(num);
    const value = siValues.findLast(v => num >= v) || 1;

    const formattedNum = (num / value).toFixed(precision_digits).replace(rx, "$1");

    return (isNegative ? "-" : "") + formattedNum + siSymbols[value];
}

export function dnColombianFormatter(num, precision_digits) {
    const siValues = [1, 1E3, 1E6, 1E9, 1E12, 1E15, 1E18];
    const siSymbols = { 1: "", 1E3: "", 1E6: "M", 1E9: "M", 1E12: "M", 1E15: "M", 1E18: "M"};

    const isNegative = num < 0;
    num = Math.abs(num);
    const value = siValues.findLast(v => num >= v) || 1;

    if (siSymbols[value] === "M") {
        num /= 1E6;
        num = formatInteger(num);
    } else {
        num = num % 1 === 0 ? formatInteger(num) : formatFloat(num, { digits: [0, precision_digits] });
    }

    return (isNegative ? "-" : "") + num + siSymbols[value];
}

export function dnNumberFormatter(dataValue, dataFormat, precision_digits){ //_onKsGlobalFormatter
    if (dataFormat === 'exact') {
        return formatFloat(dataValue, { digits: [0, precision_digits] });
    }

    const formatters = {
        'indian': dnIndianFormatter,
        'colombian': dnColombianFormatter,
        'default': dnEnglishFormatter
    };
    return (formatters[dataFormat] || formatters['default'])(dataValue, precision_digits);
}

export function ksGetCurrency(isShowCurrency, currencyType, currencyId, customCurrencySymbol) {
    if (!isShowCurrency) return { position: "before", symbol: "" };

    if (currencyType === "monetary") {
        currencyId = Array.isArray(currencyId) ? currencyId[0] : currencyId
        if (typeof currencyId !== "number")  return { position: "before", symbol: "" }
        const currency = getCurrency(currencyId);
        return currency ? { position: currency.position, symbol: currency.symbol } : { position: "before", symbol: "" };
    }

    return { position: "before", symbol: customCurrencySymbol || "" };
}

/**
 ** @params {String} csStyle - comma separated style
**/
export function formatStyle(csStyle, styleName, colorComplexity = 'lighten'){
    let style = '';
    csStyle = csStyle?.split?.(',')
    if(csStyle?.length){
        if(colorComplexity === 'darken')
            style += `${styleName} : ${ darkenColor(csStyle[0] ?? '', 0.1)};`
        else
            style += `${styleName} : ${ hexToRGBA(csStyle[0] ?? '', csStyle[1] ?? 1)};`
    }
    return style;
}

export function ks_get_gcd(a, b) {
    return (b == 0) ? a : ks_get_gcd(b, a % b);
}

export function calcDeviation(achieved, target, type) {
    let direction = type === 'absolute' ? achieved - target >= 0 : achieved >= target
    achieved = type === 'absolute' ? Math.abs(achieved - target) : achieved
    const deviation = Math.round((achieved/target) * 100)

    return {
        rawDeviation: deviation,
        direction,
        formattedDeviation: isFinite(deviation) ? `${formatInteger(deviation)} %` : String(deviation),
    }
}

export function x_multiplier(vals_list, multiplier){
    return vals_list.map( (val) => val * multiplier)
}

export function format_x_currency(config, value){
    const {
        ks_unit, ks_unit_selection, ks_currency_id, ks_chart_unit, ks_data_format, ks_precision_digits
    } = config
    const currency = ksGetCurrency(ks_unit, ks_unit_selection, ks_currency_id, ks_chart_unit)

    if(currency.position === 'after')
        return `${dnNumberFormatter(value, ks_data_format, ks_precision_digits)}  ${currency.symbol}`
    else
        return `${currency.symbol}  ${dnNumberFormatter(value, ks_data_format, ks_precision_digits)}`
}



export const dnCommonGetters = {
    isMobile() { return isMobileOS() },
    customIconUrl(config){ return `/web/image/ks_dashboard_ninja.item/${config.id}/ks_icon` },
    defaultIconClass(config){ return `fa fa-${config.ks_default_icon} fa-4x` },
    fontStyle(config){ return formatStyle(config['ks_font_color'], 'color') },
    bgColorStyle(config){ return formatStyle(config['ks_background_color'], 'background-color') },
    darkenBgColorStyle(config){ return formatStyle(config['ks_background_color'], 'background-color', 'darken') },
    iconColorStyle(config){ return formatStyle(config['ks_default_icon_color'], 'color') },
    previewCustomIconUrl(config){
        let ks_icon = config['ks_icon']
        if (isBinarySize(ks_icon)) {
            return imageUrl( 'ks_dashboard_ninja.item', config.id, 'ks_icon', { unique: config.write_date });
        } else if(ks_icon[0]) {
            const magic = fileTypeMagicWordMap[ks_icon[0]] || "png";
            return `data:image/${magic};base64,${ks_icon}`;
        }
        return '/web/static/img/placeholder.png';
    },
}

export const globalfunction = {


}

export function convert_data_to_utc(list_view_data) { // TODO Can be moved to python side
    list_view_data = JSON.parse(list_view_data);
    let datetime_format = localization.dateTimeFormat;
    let date_format = localization.dateFormat;
    if (list_view_data && list_view_data.type === "ungrouped") {
        if (list_view_data.date_index) {
            let index_data = list_view_data.date_index;
            for (let i = 0; i < index_data.length; i++) {
                for (let j = 0; j < list_view_data.data_rows.length; j++) {
                    var index = index_data[i]
                    var date = list_view_data.data_rows[j]["data"][index]
                    if (date) {
                        if (list_view_data.fields_type[index] === 'date'){
                            list_view_data.data_rows[j]["data"][index] = luxon.DateTime.fromJSDate(new Date(date + " UTC")).toFormat?.(date_format);
                        }else if(list_view_data.fields_type[index] === 'datetime'){
                            list_view_data.data_rows[j]["data"][index] = luxon.DateTime.fromJSDate(new Date(date + " UTC")).toFormat?.(datetime_format);
                        }
                    }
                }
            }
        }
    }
    return list_view_data;
}


export function eraseAllCookies(dashboard_id, cookie_name_list_to_be_deleted = []){
    cookie_name_list_to_be_deleted.forEach( (name) => {
        eraseCookie(name + dashboard_id)
    });
}

export function callItemAction(actionService, actionConfig = { action: false, domain: [], actionName: 'DnAction', resModel: false, groupBy: false}){
}

