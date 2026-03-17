
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";
import { getDomainDisplayedOperators } from "@web/core/domain_selector/domain_selector_operator_editor";
import { Domain } from "@web/core/domain";
import { useService, useBus } from "@web/core/utils/hooks";
import { treeFromDomain, domainFromTree } from "@web/core/tree_editor/condition_tree";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { getOperatorLabel } from "@web/core/tree_editor/tree_editor_operator_editor";
import { getDefaultValue, getValueEditorInfo } from "@web/core/tree_editor/tree_editor_value_editors";
import { getExpressionDisplayedOperators } from "@web/core/expression_editor/expression_editor_operator_editor";
import { KsDropDown } from "@ks_dashboard_ninja/components/custom_filter/ks_dropdown";
import { _t } from "@web/core/l10n/translation";
import { disambiguate } from "@web/core/tree_editor/utils";
import { condition, connector } from "@web/core/tree_editor/condition_tree";
import { useGetTreeDescription } from "@web/core/tree_editor/utils";
import { getSessionStorage, setSessionStorage, sessionKeys } from "@ks_dashboard_ninja/js/cookies";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { deepCopy, deepMerge } from "@web/core/utils/objects";


export class CustomFilter extends Component{
    static template = "ks_dashboard_ninja.custom_filter"
    static components = { Dropdown, DropdownItem }
    static props = {
        update: { type: Function, optional: true },
        remove: { type: Function, optional: true },
        isReset: { type: Boolean, optional: true },
        options: { type: Object, optional: true },
        data: { type: Object, optional: true },
    }
    static defaultProps = {
        update: () => {},
        domain: `[]`,
        data: {},
    }

    setup(){
        this.notification = useService("notification")
        this.loadFieldInfo = useLoadFieldInfo()
        this.getDomainTreeDescription = useGetTreeDescription()

        this.state = useState({
            rows: [],
            toggleState: true
        })

        this.facets = getSessionStorage(sessionKeys.cfFacets + this.props.options.ks_dashboard_id) ?? {}
        this.groupId = getSessionStorage(sessionKeys.cfLastGroupId + this.props.options.ks_dashboard_id) ?? 0

        onWillStart(() => this.willStart())
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps))
    }

    onPropsUpdated(nextProps){
        if(nextProps.isReset){
            this.reset()
        }
    }

    reset(){
        this.clearRows()
        this.facets = {}
        this.removeSessionStorage()
    }

    willStart(){
        const dataList = Object.values(this.props.data)
        this.loadFieldDefsAndLabels(dataList)

        const defaultOperator = getDomainDisplayedOperators(dataList[0])[0]

        this.defaultRow = {
            id: dataList[0].id,
            operator: defaultOperator,
            value: getDefaultValue(dataList[0], defaultOperator),
        }
        this.state.rows.push(deepCopy(this.defaultRow));
    }

    // Remove Data from python , we load field defs here
    async loadFieldDefsAndLabels(filters_list) {
        const promises = [];
        const filter_labels = [];
        const fieldDefs = {};
        for (const filter of filters_list) {
            filter_labels.push({ filter_name: filter.name + ' ( ' + filter.model_name + ' ) ', filter_id: filter.id})
            if (typeof filter.field_name === "string") {
                promises.push(
                    this.loadFieldInfo(filter.model, filter.field_name).then(({ fieldDef }) => {
                        fieldDefs[filter.id] = fieldDef;
                    })
                );
            }
        }
        await Promise.all(promises);
        this.fieldDefs = fieldDefs;
        this.filterLabels = filter_labels
    }

    rowFilter(filter_id){
        let filter = this.props.data[filter_id]
        return filter.name + ' ( ' + filter.model_name + ' ) '
    }

    rowOperator(row_index){
        return getOperatorLabel(this.state.rows[row_index].operator)
    }

    getOperatorInfo(filter_id) {
        const fieldDef = this.fieldDefs[filter_id];
        const operators = getDomainDisplayedOperators(fieldDef);
        const operatorList = operators.map((operator) => ({ operator: operator, label: getOperatorLabel(operator) }))

        return operatorList;
    }

    getActiveOption(options, active){
        const foundOption = options.find(option => option[0] === active);
        return foundOption ? foundOption[1] : "Select";
    }

    getValueInfo(filter_row) {
        const fieldDef = this.fieldDefs?.[filter_row.id] || this.props.data[filter_row.id];
        let valueInfo = getValueEditorInfo(fieldDef, filter_row.operator);
        if(valueInfo.component?.name === 'Select' || valueInfo.component?.name === 'List'){
            const options = fieldDef.selection || [];
            const params = {activeOption: this.getActiveOption(options, filter_row.value)}
            let KsSelectComponent = this.getKsSelectComponent(options, params)
            if(fieldDef.type === "boolean"){
                if (["is", "is_not"].includes(filter_row.operator)) {
                    const boolOptions = [
                        [true, _t("set")],
                        [false, _t("not set")],
                    ];
                    const boolParams = {activeOption: this.getActiveOption(boolOptions, filter_row.value)}
                    return this.getKsSelectComponent(boolOptions, boolParams)
                }
                const boolOptions2 = [
                    [true, _t("True")],
                    [false, _t("False")],
                ];
                const boolParams2 = {activeOption: this.getActiveOption(boolOptions2, filter_row.value)}
                return this.getKsSelectComponent(boolOptions2, boolParams2)
            }
            if(valueInfo.component?.name === 'List'){
                let editorInfo = getValueEditorInfo(fieldDef, "=", {
                    addBlankOption: true,
                    startEmpty: true,
                });
                if(editorInfo.component?.name === 'Select'){
                    editorInfo = KsSelectComponent
                    valueInfo.extractProps = ({ value, update }) => {
                        if (!disambiguate(value)) {
                            const { stringify } = editorInfo;
                            editorInfo.stringify = (val) => stringify(val, false);
                        }
                        return {
                            value,
                            update,
                            editorInfo,
                        };
                    }
                }
                return valueInfo;
            }
            return KsSelectComponent;
        }
        return valueInfo;
    }

    getKsSelectComponent(options, params){
        const getOption = (value) => options.find(([v]) => v === value) || null;
        return {
            component: KsDropDown,
            extractProps: ({ value, update }) => ({
                value,
                update,
                options,
                addBlankOption: params.addBlankOption,
                activeOption: params.activeOption || "Select"
            }),
            isSupported: (value) => Boolean(getOption(value)),
            defaultValue: () => options[0]?.[0] ?? false,
            stringify: (value, disambiguate) => {
                const option = getOption(value);
                return option ? option[1] : disambiguate ? formatValue(value) : String(value);
            },
            message: _t("Value not in selection"),
        };
    }

    getDefaultOperator(fieldDef) {
        return getExpressionDisplayedOperators(fieldDef)[0];
    }

    addRow(){
        this.state.rows.push(deepCopy(this.defaultRow))
    }

    deleteRow(rowIndex){
        this.state.rows.splice(rowIndex, 1)
    }

    clearRows(){
        this.state.rows = [deepCopy(this.defaultRow)];
    }

    selectRowFilter(filterId, rowIndex) {
        const fieldDef = this.fieldDefs[filterId];
        const operator = this.getDefaultOperator(fieldDef)
        this.state.rows[rowIndex] = {
            id: filterId,
            operator: operator,
            value: getDefaultValue(fieldDef, operator),
        }
    }

    // TODO: remove uid from here
    selectRowValue(rowIndex, value){
        let fieldType = this.props.data[this.state.rows[rowIndex]?.id].type
        let operator = this.state.rows[rowIndex]?.operator
        if(fieldType && ['many2many', 'many2one', 'one2many'].includes(fieldType)){
            if (Array.isArray(value)) {
                value =  value.flatMap(
                    item => {
                        if(item === "%UID") {
                            return user.userId;
                        } else if (item === "%MYCOMPANY") {
                            return ["in", "not in"].includes(operator) ? this.env.services.company.activeCompanyIds : this.env.services.company.activeCompanyIds[0];
                        } else {
                            return item;
                        }
                    }
                );
            }
            else if(typeof value === 'string'){
                if(value === "%UID") {
                    value =  user.userId;
                } else if (value === "%MYCOMPANY") {
                    value = this.env.services.company.activeCompanyIds[0];
                }
            }
        }
        this.state.rows[rowIndex].value = value
    }

    selectRowOperator(operator, rowIndex){
        const fieldDef = this.fieldDefs[this.state.rows[rowIndex].id]
        this.state.rows[rowIndex].operator = operator
        this.state.rows[rowIndex].value = getDefaultValue(fieldDef, operator, this.state.rows[rowIndex].value)
    }

    removeSessionStorage(){
        sessionStorage.removeItem(sessionKeys.cfFacets + this.props.options.ks_dashboard_id)
        sessionStorage.removeItem(sessionKeys.cfLastGroupId + this.props.options.ks_dashboard_id)
    }

    setSessionStorage(){
        setSessionStorage(sessionKeys.cfFacets + this.props.options.ks_dashboard_id, this.facets, this.notification)
        setSessionStorage(sessionKeys.cfLastGroupId + this.props.options.ks_dashboard_id, this.groupId, this.notification)
    }

    async applyFilters() {
        this.removeSessionStorage()
        const rows = this.state.rows;
        let modelConnectors = {}

        let modelNameMap = {}

        for (const row of rows) {
            const { model, field_name, model_name } = this.props.data[row.id];
            const { operator, value } = row

            modelNameMap[model] = model_name
            modelConnectors[model] ??= connector('|')

            modelConnectors[model].children.push(condition(field_name, operator, value))
        }

        let modelSubDomains = {}
        let facetExtension = {}

        for( let model of Object.keys(modelConnectors)){
            let domain = new Domain(domainFromTree(modelConnectors[model])).toList();
            let label = await this.getDomainTreeDescription(model, modelConnectors[model])

            let isError = await this.validateDomain(model, domain)

            if(isError) return;

            let facetSubExtension = {
                [model]: {
                    groups: {
                        [`customFilter_${++this.groupId}`]: {
                            label,
                            domain
                        }
                    },
                    model_name: modelNameMap[model]
                }
            }

            facetExtension = deepMerge(facetExtension, facetSubExtension)

            modelSubDomains[model] = {
                [`customFilter_${this.groupId}`]: domain
            }
        }

        this.clearRows()
        this.updateFacets(facetExtension)
        this.props.update(modelSubDomains)
        this.setSessionStorage()

    }

    updateFacets(extension){
        this.facets = deepMerge(this.facets, extension)
    }


    async validateDomain(model, domain){
        let isValid;
        try {
            const evalContext = { ...user.context };
            domain = new Domain(domain).toList(evalContext);
        } catch {
            isValid = false;
        }
        if (isValid === undefined) {
            isValid = await rpc("/web/domain/validate", { model, domain });
        }
        if (!isValid) {
            this.notification.add(_t("Domain is invalid. Please correct it"), { type: "danger" });
            return true;
        }
        return false;
    }

    onRemoveFacet(model, group){
        this.removeSessionStorage()
        delete this.facets[model].groups[group];

        if(!Object.keys(this.facets[model].groups).length)
            delete this.facets[model];

        this.props.remove({ [model]: { [group]: group } })
        this.setSessionStorage()
        this.state.toggleState = !this.state.toggleState
    }

}

