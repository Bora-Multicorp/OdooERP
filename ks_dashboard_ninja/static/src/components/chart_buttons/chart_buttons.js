
import { Component, onMounted, useRef, whenReady } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService, useForwardRefToParent } from "@web/core/utils/hooks";
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';
import { download } from "@web/core/network/download";
import { BlockUI } from "@web/core/ui/block_ui";
import { ks_get_current_gridstack_config, formatStyle } from '@ks_dashboard_ninja/js/dn_utils';
import { isMobileOS } from "@web/core/browser/feature_detection";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { pick } from "@web/core/utils/objects";
import { ChartInsights } from '@ks_dashboard_ninja/components/charts_insights/chart_insights';

/*
* The flow for this component is tobe like - it takes all the methods and data to be used as props, and just use them on button clicks
*/

export class KsItemButton extends Component{

    // TODO: check while adding property of some obj , does it refers to same value or diff
    static props = {
        itemComponent: { type: Function },
        chartInsightsProps: { type: Function, optional: true },
        itemConfig: { type: Object, optional: true },
        rootClasses: { type: String },
        itemRootRef: { type: Object, optional: true },
        dnStore: { type: Object, optional: true },
        fetchOrUpdateItem: { type: Function, optional: true },
        updateChartColor: { type: Function, optional: true },
        resetChart: { type: Function, optional: true },
        isDashboardManager: { type: Boolean },
        drillDownActionLength: { type: Number, optional: true },
        allDashboardLists: { type: Array },
        itemBasicDataFields: { type: Object },
        itemActions: { type: Object, optional: true },
        listConfig: { type: Object, optional: true },   // list view dynamic data
        graphConfig: { type: [Object, Boolean], optional: true },  // graph view dynamic data
    }

//
    static template = "ks_dashboard_ninja.ks_chart_buttons"

    setup(){
        // TODO: check if multiple companies are selected
        this.activeCompanyName = this.env.services.company.currentCompany.name
        this.itemId = this.props.itemConfig.id
        this.rootRef = useRef('rootRef')
        this.resetChart = useForwardRefToParent('resetChart')
        this.uiService = useService("ui");
        this.store = useService("mail.store");
        this.notification = useService("notification")
        this.dialogService = useService("dialog")
        this.orm = useService("orm")
        this.chartColors = ["default", "dark", "moonrise", "material"]

        this.selectedDashboardId = this.props.allDashboardLists[0]['id']

    }



    get buttonColorStyle(){
        return formatStyle(this.props.itemConfig.ks_button_color, 'color')
    }

    get isMobile(){
        return isMobileOS()
    }

    get itemDescription(){
        // TODO: Put \n functionality in help or a note in ui and check ui of info
        let descriptionList = this.props.itemConfig.ks_info.replace?.(/\\n/g, '\n').split?.('\n')
        return descriptionList || []
    }

    get buttonsVisibility(){
        let manager = this.props.isDashboardManager
        let itemType = this.props.itemConfig.ks_dashboard_item_type
        let charts = ['ks_bar_chart', 'ks_horizontalBar_chart', 'ks_line_chart', 'ks_area_chart', 'ks_pie_chart',
                      'ks_doughnut_chart', 'ks_polarArea_chart', 'ks_radialBar_chart', 'ks_scatter_chart', 'ks_funnel_chart',
                      'ks_bullet_chart', 'ks_flower_view', 'ks_radar_view']
        return {
            'move-duplicate': manager && !this.isMobile,
            'quick-customise': manager && !this.isMobile,
            'item-info': true,
            'reset-chart': manager && !this.isMobile,
            'more': manager && !this.isMobile,
            'chart-exporting-options': manager && !this.isMobile && (charts.includes(itemType) || itemType === 'ks_list_view'),
            'chart-color': manager && charts.includes(itemType) && !this.isMobile,
        }
    }

    resetCb(){
        this.props.dnStore.delete(this.itemId)
        this.props.fetchOrUpdateItem()
    }

    async openDiscussChannelPopup(){
        let internal_chat_thread;
        let channelId = await rpc("/web/dataset/call_kw/discuss.channel/getId",{
            model: 'discuss.channel',
            method: 'ks_chat_wizard_channel_id',
            args: [[], this.itemId, this.props.itemConfig.ks_dashboard_id],
            kwargs:{
                dashboard_name: this.props.itemConfig.ks_dashboard_name,
                item_name: this.props.itemConfig.name,
            }
        })

        // FIXME : Dont close all chat popover windows . only close those ones belong belongs to dashboard


        this.store.chatHub.opened?.forEach?.( (visibleChatWindow) => {
            visibleChatWindow.close?.()
        })

        if(channelId)   internal_chat_thread = await this.store.Thread.getOrFetch({ model: "discuss.channel", id: channelId})
        if(internal_chat_thread){
            if(internal_chat_thread.name)   internal_chat_thread.name = this.props.itemConfig.ks_dashboard_name + ' - ' + this.props.itemConfig.name
            internal_chat_thread.open()
        }

    }

    handleDropdowns(ev){
        let targetDropdown = ev.target.closest('.dropdown-toggle')
        this.rootRef.el.querySelectorAll('.dropdown-toggle').forEach((dropdown) => {
            if(targetDropdown !== dropdown)     Dropdown.getInstance(dropdown)?.hide()
        })
    }

    openItemFormView(){
        this.dialogService.add(FormViewDialog,{
            resModel: 'ks_dashboard_ninja.item',
            title: 'Edit Chart',
            resId : this.itemId,
            is_expand_icon_visible: true,
            context: {
                'form_view_ref': 'ks_dashboard_ninja.item_form_view',
                'form_view_initial_mode': 'edit',
                'ks_form_view': true
            },
            onRecordSaved: (record) => {
                delete this.props.dnStore.data[this.itemId]

                let itemBasicData = pick(record.data, ...this.props.itemBasicDataFields)
                this.env.bus.trigger('MODIFY: Dashboard ITEM', { isUpdate: true, itemsDataToUpdate: [itemBasicData]})
            },
            size: 'fs'
        });
    }

    async exportAsJson(){
        const data = { 'header': this.props.itemConfig.name, item_id: this.itemId }
        await download({
            url: '/ks_dashboard_ninja/export/item_json',
            data: { data: JSON.stringify(data) },
        });
    }

    async duplicateItem(){
        let newItemId = await rpc("/web/dataset/call_kw/ks_dashboard_ninja.item/copy", {
                                model: 'ks_dashboard_ninja.item',
                                method: 'copy',
                                args: [[this.itemId], { 'ks_dashboard_ninja_board_id': parseInt(this.selectedDashboardId) }],
                                kwargs:{},
                            })
        let dashboard_name = this.props.allDashboardLists.filter( (dashboard) => dashboard.id === parseInt(this.selectedDashboardId))[0]?.name;

        if(this.props.itemConfig.ks_dashboard_id == this.selectedDashboardId){
            let itemDataToAdd = pick(this.props.itemConfig, ...this.props.itemBasicDataFields)
            itemDataToAdd.id = newItemId[0]
            this.env.bus.trigger('MODIFY: Dashboard ITEM', { isAdd: true, itemsDataToAdd: [itemDataToAdd]})
        }

        this.notification.add(_t('Selected item is duplicated to ' + dashboard_name + '.'),{ title: _t("Item Duplicated"), type: 'success' })


    }


    async moveItem(){
        if(this.props.itemConfig.ks_dashboard_id != this.selectedDashboardId){
            await this.orm.write('ks_dashboard_ninja.item', [this.itemId], { 'ks_dashboard_ninja_board_id': parseInt(this.selectedDashboardId) }, {})
            let itemDataToRemove = pick(this.props.itemConfig, ...this.props.itemBasicDataFields)
            this.env.bus.trigger('MODIFY: Dashboard ITEM', { isRemove: true, itemDataToRemove})

        }

        let dashboard_name = this.props.allDashboardLists.filter( (dashboard) => dashboard.id === parseInt(this.selectedDashboardId))[0]?.name
        this.notification.add(_t('Selected item is moved to ' + dashboard_name + '.'), { title: _t("Item Moved"), type: 'success' });
    }

    async deleteItem(e){
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Are you sure that you want to remove this item?"),
            confirmLabel: _t("Delete Item"),
            title: _t("Delete Dashboard Item"),
            confirm: () => {
                let itemDataToRemove = pick(this.props.itemConfig, ...this.props.itemBasicDataFields)
                this.env.bus.trigger('MODIFY: Dashboard ITEM', { isRemove: true, itemDataToRemove})
                this.orm.unlink('ks_dashboard_ninja.item', [this.itemId])
                return true;
            },
        });
    }

    checkDrillDown(featureName){
        if(this.props.drillDownActionLength > 1){
            this.notification.add(_t( featureName + " is not available in drill down charts"), { type: "info" })
            return true
        }
        return false
    }

    openChartInsights(){
        if(this.checkDrillDown("Chart Insights"))   return

        this.env.services.dialog.add(ChartInsights, {
            itemComponentInfo: {
                component: this.props.itemComponent,
                props: {
                    itemConfig: {
                        ...this.props.itemConfig,
                        ks_chart_data: { ...this.props.graphConfig },
                        ks_list_view_data: { ...this.props.listConfig },
                    },
                    itemId: this.props.itemConfig.id,
                    isAIExplanation: true,
                    isPreview: true,
                },
            },
            onSave: () => {
                delete this.props.dnStore.data[this.itemId]
                this.props.fetchOrUpdateItem()
            }
        })
    }

    async updateChartColor(chartColor){

        if(this.checkDrillDown("Color Options"))   return

        this.props.updateChartColor(chartColor)
        await this.orm.write('ks_dashboard_ninja.item', [this.itemId], { "ks_chart_item_color": chartColor })
    }

    async exportAsXlsCsv(format) {
        try {
            this.uiService.block();

            let data = {};
            if (this.props.itemConfig.ks_dashboard_item_type === "ks_list_view") {
                format = "list_" + format;
                data = {
                    res_id: this.itemId,
                    header: this.props.itemConfig.name,
                    domain: this.props.itemActions?.domain || [],
                    context: { export_all: true, ...(this.props.itemActions?.context ?? {}) },
                };
            } else {
                format = "chart_" + format;
                data = {
                    header: this.props.itemConfig.name,
                    chart_data: this.props.graphConfig,
                };
            }

            await download({
                url: "/ks_dashboard_ninja/export/" + format,
                data: { data: JSON.stringify(data) },
            });

        } catch (err) {
            console.error("Export failed:", err);
        } finally {
            this.uiService.unblock();
        }
    }

    async exportAsPdf(){
        if(this.checkDrillDown("Export Pdf"))   return

        let image = await this.getItemImg()
        let payload = {
            content: [{ image, width: 500, height: this.props.itemRootRef.el.offsetHeight > 750 ? 750 : this.props.itemRootRef.el.offsetHeight }],
            images: { bee: image }
        }

        pdfMake.createPdf(payload).download(this.props.itemConfig.name + '.pdf')

    }

    async getItemImg(){
        let canvas = await html2canvas(this.props.itemRootRef.el, { useCORS: true, allowTaint: false })
        return canvas.toDataURL("image/png")
    }

    async exportAsImg(){
        if(this.checkDrillDown("Export Image"))   return

        let image = await this.getItemImg()

        let linkEl = document.createElement('a')
        linkEl.href =  image;
        linkEl.download = this.props.itemConfig.name + 'png'
        document.body.appendChild(linkEl)
        linkEl.click()
        document.body.removeChild(linkEl)
    }

}
