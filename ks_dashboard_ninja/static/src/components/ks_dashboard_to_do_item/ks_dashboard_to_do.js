/** @odoo-module **/
import { Component, onWillStart, useState ,onMounted, onWillRender,useRef,onWillPatch, useEffect } from "@odoo/owl";
import { globalfunction } from '@ks_dashboard_ninja/js/dn_utils';
import { loadBundle } from "@web/core/assets";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";
import { TodoEditDialog } from "@ks_dashboard_ninja/components/ks_dashboard_to_do_item/edit_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { KsItemButton } from '@ks_dashboard_ninja/components/chart_buttons/chart_buttons';
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { standardDashboardItemProps, standardDashboardItemDefaultProps, formatStyle } from '@ks_dashboard_ninja/js/dn_utils';
import { setupItemEventBus } from '@ks_dashboard_ninja/js/access_utils';
import { Chart } from "@ks_dashboard_ninja/components/dashboard_items/chart/chart";


export class DNTodo extends Chart{

    setup(){
        super.setup()
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            config: this.props.itemConfig ?? false,
            activeHeaderTabIndex: 0
        })
        this.todoRootRef = useRef("todoRootRef");
        if(this.props.isFormPreview)  this.parseTodoConfigs()

        this.allowItemFetching = true

        setupItemEventBus(this.env.bus, this.props)

        useEffect( () => {
        }, () => [])

        onWillPatch( () => {
            if(this.props.isFormPreview)  this.parseTodoConfigs()
        })
    }

    get isMobile() {
        return isMobileOS();
    }

    get bgColorStyle(){
        return formatStyle(this.state.config.ks_header_bg_color, 'background-color')
    }

    get fontColorStyle(){
        return formatStyle(this.state.config.ks_font_color, 'color')
    }

    get ksIsDashboardManager(){
        return this.ks_dashboard_data.ks_dashboard_manager;
    }

    get ksIsUser(){
        return true;
    }

    get ks_dashboard_list(){
        return this.ks_dashboard_data.ks_dashboard_list;
    }

    parseTodoConfigs(){
        let config = typeof this.state.config.ks_to_do_data === 'string' ?
                        JSON.parse(this.state.config.ks_to_do_data) : this.state.config.ks_to_do_data
        this.state.config.ks_to_do_data = config
    }

    async fetchOrUpdateItem() {

        this.hideRefreshButton()
        this.allowItemFetching = false

        let config = await this.props.dnStore.getData(this.props.itemId, { 'ks_domain_1': [] }, {})
        this.state.config = config
        this.state.activeHeaderTabIndex = 0
    }

    changeHeaderLine(headerLineIndex){
        this.state.activeHeaderTabIndex = headerLineIndex
    }

    addDescriptionLine(){
        if(!this.state.config.ks_to_do_data.length){
            this.notification.add(_t("No header lines present.Please add through quick customise"), { type: "info" })
            return;
        }

        this.dialogService.add(TodoEditDialog,{
            inputText: '',
            title: 'Create Description Line',
            confirm: async (descriptionName) => {
                let vals = { ks_description: descriptionName, ks_to_do_header_id: this.state.config.ks_to_do_data[this.state.activeHeaderTabIndex].id }
                let newDescriptionLineId = await this.orm.create('ks_to.do.description', [vals])
                vals['id'] = newDescriptionLineId[0]

                this.state.config.ks_to_do_data[this.state.activeHeaderTabIndex].ks_to_do_description_lines.push(vals)
            },
        });
    }

    editDescriptionLine(description_line){
        this.dialogService.add(TodoEditDialog,{
            inputText: description_line.ks_description,
            title: 'Edit Description Line',
            confirm: async (descriptionName) => {
                if(description_line.ks_description === descriptionName) return

                description_line.ks_description = descriptionName
                await this.orm.write('ks_to.do.description', [description_line.id], { 'ks_description': descriptionName})
            },
        });
    }

    deleteDescriptionLine(description_line){
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Do you want to delete this description line ?"),
            confirm: async () => {
                await this.orm.unlink('ks_to.do.description', [description_line.id])

                let descriptionLines = this.state.config.ks_to_do_data[this.state.activeHeaderTabIndex]
                const index = descriptionLines.ks_to_do_description_lines.findIndex(line => line.id === description_line.id)
                if (index !== -1) {
                    descriptionLines.ks_to_do_description_lines.splice(index, 1)
                }

            },
        });
    }

    async toggleActive(description_line){
        await this.orm.write('ks_to.do.description', [description_line.id], { 'ks_active': !description_line.ks_active })
        description_line.ks_active = !description_line.ks_active
    }

};

DNTodo.props = {
    ...standardDashboardItemProps(),
};

DNTodo.components = { TodoEditDialog, KsItemButton }
DNTodo.template = "ks_dashboard_ninja.to_do_renderer";
