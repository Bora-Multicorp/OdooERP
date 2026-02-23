
import { Component, useState, onWillRender, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useForwardRefToParent } from "@web/core/utils/hooks";
import { download } from "@web/core/network/download";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { KsDateFilter } from '@ks_dashboard_ninja/components/date_filter/date_filter';
import { KSItemsRowStructure } from '@ks_dashboard_ninja/components/ks_items_structures/row_structure';
import { KSItemsGridStructure } from '@ks_dashboard_ninja/components/ks_items_structures/grid_structure';
import { KsItems } from '@ks_dashboard_ninja/components/ks_items/ks_items';
import { ks_get_current_gridstack_config } from '@ks_dashboard_ninja/js/dn_utils'
import { DNFilter } from '@ks_dashboard_ninja/components/dn_filter/dn_filter';
import { isMobileOS } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { FormViewDialog} from '@web/views/view_dialogs/form_view_dialog';
import { useService } from "@web/core/utils/hooks";
import { eraseAllCookies } from '@ks_dashboard_ninja/js/dn_utils';
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { pick } from "@web/core/utils/objects";
import { deepCopy } from "@web/core/utils/objects";

// TODO: the manager issue is present - explain the issue in coment here

export class KsHeader extends Component {
    static props = {
        dashboardData: { type: Object, optional: true },
        itemsBasicData: { type: Object, optional: true },
        mode: { type: String },
        dashboardActions: { type: Object, optional: true },
        dashboardRootRef: { type: Object, optional: true },
        DNGridStack: { type: Object, optional: true },
        dnStore: { type: Object, optional: true },
    }
    static components = { Dropdown, DropdownItem, KsDateFilter, DNFilter }
    static template = "ks_dashboard_ninja.Ks_dashboard_ninja_header"


    setup(){
        this.uiService = useService("ui")
        this.orm = useService("orm")
        this.actionService = useService("action")
        this.dialogService = useService("dialog")
        this.menuService = useService("menu")
        this.notification = useService("notification")
        this.ks_dashboard_id = this.props.dashboardData.id
        this.isMobile = isMobileOS();
        this.headerRootRef = useForwardRefToParent("headerRootRef");
        this.importRef = useRef("importRef")
        this.layoutNameRef = useRef("layoutNameRef")



        this.state = useState({
            mode: this.props.mode ,    // types - [ "manager", "user", "mobile", "custom_date" ]
            isDashboardBookmarked: this.props.dashboardData.is_bookmarked,
            modeCount: 0
        });
    }

    updateMode(mode){
        this.state.modeCount++
        if(mode){
            this.state.mode = mode
            return
        }
        this.state.mode = this.props.dashboardData.ks_dashboard_manager ? "manager" : "user"
    }

    // TODO: what if we need to show buttons in one mode but not in another mode, like in user mode dont show edit button

    get dropdowns(){
        return [
            {   name: "Edit Layout", modes: ["manager"],
                func: () => this.editGsLayout(), svg: "ks_dashboard_ninja.header_edit_svg" },
            {   name: "Bookmark Dashboard", modes: ["manager", "user", "custom_date"],
                func: () => this.updateBookmark(), svg: "ks_dashboard_ninja.bookmark" },
            {   name: "Capture Dashboard", modes: ["manager", "user", "custom_date"],
                func: () => this.dashboardImageUpdate(), svg: "ks_dashboard_ninja.capture" },
            {   name: "Settings", svg: "ks_dashboard_ninja.setting", modes: ["manager"],
                dropdown_items: [
                    { name: "Dashboard Settings" , svg: "ks_dashboard_ninja.setting-2",
                      func: () => this.openDashboardFormView(), class : '', modes: ["manager", "custom_date"] },
                    { name: "Delete the Dashboard", svg: "ks_dashboard_ninja.trash_svg",
                      func: this.deleteDashboard.bind(this), class : '', modes: ["manager", "custom_date"] },
                    { name: "Create New Dashboard", svg: "ks_dashboard_ninja.add-square",
                      func: () => this.openCreateDashboardWizard(), class : '', modes: ["manager", "custom_date"] },
                    { name: "Generate Dashboard with AI", svg: "ks_dashboard_ninja.illustrator",
                      func: () => this.generateDashboardWithAi(), class : '', modes: ["manager", "custom_date"] },
                    { name: "Duplicate Current Dashboard", svg: "ks_dashboard_ninja.copy",
                      func : (ev) => this.openDuplicateDashboardWizard(ev), class : '', modes: ["manager", "custom_date"] }
                ]
            },
            {   name: "More", svg: "ks_dashboard_ninja.more", modes: ["manager", "user"],
                dropdown_items: [
                    { name: "Import Item" , svg: "ks_dashboard_ninja.download_svg",
                      func: () => this.importItem(), class : '', modes: ["manager"],},
                    { name: "Export Dashboard", svg: "ks_dashboard_ninja.document-upload",
                      func: () => this.exportDashboard(), class : '', modes: ["manager", "user", "custom_date"],},
                    { name: "Import Dashboard", svg: "ks_dashboard_ninja.download_svg",
                     func: () => this.importDashboard(), class : '', modes: ["manager"] }
                 ]
            },
        ]
    }

    get header_mode_buttons(){
        return {
            "edit": {
                buttons: [
                            { name: "Discard", callback: this.discardEditedLayout.bind(this),
                              classes: 'dash-default-btn bg-white me-2', shouldVisible: true },
                            { name: "Save as New Layout", callback: this.saveEditedLayoutAsNew.bind(this),
                              classes: 'dash-btn-red me-2 ks-bg-violet', shouldVisible: this.multiLayout },
                            { name: "Save Layout", callback: this.saveEditedLayout.bind(this),
                              classes: 'dash-btn-red', shouldVisible: true }
                          ]
            },
        }
    }

    get defaultLayout(){
        return this.props.dashboardData.gs_layouts_info.defaultLayout
    }

    get multiLayout(){
        return this.props.dashboardData.gs_layouts_info.multiLayout
    }

    dashboardImageUpdate(){
        let image_element = document.querySelector('.ks_dashboard_main_content');
        if(!document.querySelector('.ks_dashboard_main_content')?.childNodes.length){
            image_element = document.querySelector('.main-box');
        }
        let self = this;
        this.uiService.block();
        let canvas = html2canvas(image_element,  {
                          height: image_element.clientHeight + 186,
                          width: image_element.clientWidth,
                          windowWidth: image_element.scrollWidth,
                          windowHeight: image_element.scrollHeight,
                          scrollY: 0,
                          scrollX: 0,
                          x: image_element.scrollLeft,
                          y: image_element.scrollTop < 600 ? image_element.scrollTop < 50 ? image_element.scrollTop :
                                    image_element.scrollTop - 150 : image_element.scrollTop - 650,
                        }).then((canvas) => {
                                    let image = canvas.toDataURL("image/png");
                                    rpc("/web/dataset/call_kw/ks_dashboard_ninja.board/saveImage",{
                                                        model: 'ks_dashboard_ninja.board',
                                                        method: 'save_dashboard_image',
                                                        args: [[self.ks_dashboard_id]],
                                                        kwargs:{image: image},
                                                    }).then((result) => {
                                                            this.uiService.unblock();
                                                    });
        });
        this.notification.add(
            _t('Dashboard image updated successfully!'), { title: _t("Image Refreshed"), type: 'success' }
        )
    }

    async updateBookmark(){
        let updatedBookmarks = await this.orm.call("ks_dashboard_ninja.board", 'update_bookmarks', [[this.ks_dashboard_id]], {});
        updatedBookmarks = updatedBookmarks[1]
        // TODO: Update here
        this.state.isDashboardBookmarked = !this.state.isDashboardBookmarked

        this.notification.add(
            _t(`Dashboard ${ updatedBookmarks ? "added to" : "removed from"} your bookmarks`),
            { title:_t(`Bookmark ${ updatedBookmarks ? "Added" : "Removed"}`), type: 'success' }
        )
    }

    itemsPresence(){
        if(this.props.itemsBasicData.length)  return true

        this.notification.add(_t('No Items!'),{ title:_t("Create some items"), type: 'info'});
        return false;
    }

    createNewItem() {
        this.dialogService.add(FormViewDialog, {
            resModel: 'ks_dashboard_ninja.item',
            is_expand_icon_visible: true,   // TODO: Should be removed
            context: {
                'ks_dashboard_id': this.ks_dashboard_id,
                'ks_dashboard_item_type': 'ks_tile',
                'form_view_ref': 'ks_dashboard_ninja.item_form_view',
                'form_view_initial_mode': 'edit',
                'ks_set_interval': this.props.dashboardData.ks_set_interval,
                'ks_data_formatting': this.props.dashboardData.ks_data_formatting,
                'ks_form_view': true
            },
            onRecordSaved: (record) => {
                // TODO: Update here
                let itemDataToAdd = pick(record.data, ...this.props.dashboardData.item_basic_data_fields)
                itemDataToAdd.id = record.resId

                this.props.dashboardActions.addItem?.([itemDataToAdd])
            },
            size: "fs",
            title: "Create New Chart"
        });

    }

    openDashboardFormView(){

        this.dialogService.add(FormViewDialog, {
            resModel: 'ks_dashboard_ninja.board',
            resId: this.ks_dashboard_id,
            is_expand_icon_visible: true,   // TODO: Should be removed
            context: {
                'form_view_initial_mode': 'edit',
                'create': false,
            },
            onRecordSaved: (record) => this.props.dashboardActions.refreshDashboardData?.(record),  // TODO: Update here
            size: "lg",
            title: "Dashboard Settings"
        });
    }

    openCreateDashboardWizard(){
        this.actionService.doAction({
            name: _t('Add New Dashboard'),
            type: 'ir.actions.act_window',
            res_model: 'ks.dashboard.wizard',
            views: [ [false, 'form']],
            view_mode: 'form',
            target: 'new',
        })
    }

    async openDuplicateDashboardWizard(){
//        FIXME: why this rpc is made for getting action ??? can be directly initialize here - require python changes
        let action = await this.orm.call('ks.dashboard.duplicate.wizard', 'DuplicateDashBoard', [[this.ks_dashboard_id]], {})
        this.actionService.doAction(action)
    }

    async exportDashboard(){
        let dashboard_id = JSON.stringify(this.ks_dashboard_id);
        // FIXME: why dashboard_id is stringified , send in both args and kwargs - python changes should be done
        let result = await this.orm.call('ks_dashboard_ninja.board', 'ks_dashboard_export', [dashboard_id], { dashboard_id: dashboard_id })

        download({
            data: { data: JSON.stringify({"header": 'dashboard_ninja', "dashboard_data": result}) },
            url: '/ks_dashboard_ninja/export/dashboard_json',
        })
    }

    // TODO: the flow for  updating mode is not best - it can be updated

    async selectGsLayout(layout){
        this.props.DNGridStack.changeGrid(layout.grid_stack_config)

        const args = [[this.ks_dashboard_id], layout.id, { is_default: true }, true]
        let gs_layouts = await this.orm.call('ks_dashboard_ninja.board', 'layout_changes', args, {})
        this.props.dashboardData.gs_layouts_info.setGsLayouts(gs_layouts)
        this.updateMode()
    }

    discardEditedLayout(){
        this.props.DNGridStack.changeGrid(this.defaultLayout.grid_stack_config)
        this.props.DNGridStack.makeStatic()
        this.updateMode()
    }

    editGsLayout() {
        if(!this.itemsPresence())   return;
        this.props.DNGridStack.makeEditable()
        this.updateMode('edit')
    }

    async saveEditedLayout(){
        if(this.checkName(this.layoutNameRef.el?.value))  return

        this.props.DNGridStack.setEditedLayout(this.defaultLayout)

        const args = [[this.ks_dashboard_id], this.defaultLayout.id, { name: this.layoutNameRef.el?.value }, false]
        let gs_layouts = await this.orm.call('ks_dashboard_ninja.board', 'layout_changes', args, {})
        this.props.dashboardData.gs_layouts_info.setGsLayouts(gs_layouts)
        this.updateMode()
    }

    checkName(name) {
        if(name === "") {
            this.notification.add(_t("Name is required to save."), { type: 'warning' })
            return true
        }
        return false
    }

    async saveEditedLayoutAsNew() {
        if(this.checkName(this.layoutNameRef.el?.value))  return

        this.props.DNGridStack.makeStatic()

        let vals = {
            'name': this.layoutNameRef.el?.value,
            'dn_dashboard_id': this.ks_dashboard_id,
            'grid_stack_config': this.props.DNGridStack.currentGsConfig(),
            'is_default': true,
            'is_main_layout': false
        }

        const args = [[this.ks_dashboard_id], null, vals, true]
        let gs_layouts = await this.orm.call('ks_dashboard_ninja.board', 'layout_changes', args, {})

        this.props.dashboardData.gs_layouts_info.setGsLayouts(gs_layouts)
        this.updateMode()
    }

    deleteDashboard(){
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Are you sure you want to delete this dashboard ?"),
            confirmLabel: _t("Delete Dashboard"),
            title: _t("Delete Dashboard"),
            confirm: async () => {
                await  this.orm.unlink('ks_dashboard_ninja.board', [this.ks_dashboard_id])
                await this.menuService.reload()

                this.notification.add(_t('Dashboard Deleted Successfully'), { title: _t("Deleted"), type: 'success' })

                const currentAppId = this.menuService?.getCurrentApp()?.id
                await this.menuService.selectMenu(currentAppId)
            },
        });
    }

    async openGenerateAiDialog(ev){

        // FIXME: Logic for getting AI Items ?? why creating new dashboard And creating chart ?? , it is very bad logic
        // FIXME: this tempid logic is written only to get transient modal id and from it get ai dashboard id in discard method below

        const tempId = await this.orm.create('ks_dashboard_ninja.arti_int', [{}])

        this.dialogService.add(FormViewDialog,{
            resModel: 'ks_dashboard_ninja.arti_int',
            resId: tempId[0],
            title: 'Generate items with AI',
            is_expand_icon_visible: true,
            onRecordSaved: async (record) => {
                if(record.data.created_dashboard_id){
                    let itemsBasicData = await this.orm.searchRead('ks_dashboard_ninja.item', [["ks_dashboard_ninja_board_id", "=", record.data.created_dashboard_id]],
                                                        this.props.dashboardData.item_basic_data_fields)

                    // TODO: logic to delete , ai dashboard
                    this.dialogService.add(KSItemsGridStructure, {
                        componentInfo: {
                            component: KsItems,
                            props: {
                                itemsBasicData: itemsBasicData,
                                dashboardData: { id: record.data.created_dashboard_id },
                                isGridStructure: true,
                                isItemsPreview: true,
                                isGridStack: false,
                                dnStore: this.props.dnStore,
                            }
                        }
                    })

                }
                else if(record.data.created_item_id){
                    let itemDataToAdd = await this.orm.read('ks_dashboard_ninja.item', [record.data.created_item_id], this.props.dashboardData.item_basic_data_fields)
                    if(itemDataToAdd[0])    this.props.dashboardActions.addItem?.([itemDataToAdd[0]])
                }
                else
                    return
            },
            onRecordDiscarded: async () => {
                let aiDashboardId = await this.orm.read('ks_dashboard_ninja.arti_int', [tempId[0]], ['created_dashboard_id'], {})
                aiDashboardId = aiDashboardId[0].created_dashboard_id

                if(aiDashboardId){
                    await this.orm.unlink('ks_dashboard_ninja.board', [aiDashboardId])
                }
            },
            context: {
                'ks_dashboard_id': this.ks_dashboard_id, 'ks_form_view' : true,
                'generate_dialog' : true, dialog_size: 'extra-large',
            }
        })
    }

    async importDashboard(){
        this.dialogService.add(FormViewDialog, {
            resModel: 'ks_dashboard_ninja.import',
            is_expand_icon_visible: true,   // TODO: Should be removed
            context: { 'create': false },
            onRecordSaved: async (record) => {
                await this.menuService.reload()
                this.notification.add(_t(" Dashboard Successfully Imported "), { type: 'success' })
            },
            size: "lg",
            title: "Import Dashboard"
        })
    }

    importItem() {
        this.importRef.el.click()
    }

    onFileChange() {
        const fileReader = new FileReader()
        fileReader.onload = async () => {
            this.importRef.el.value = ''

            let kwargs = {
                file: fileReader.result,
                dashboard_id: this.ks_dashboard_id
            }
            let args = [this.ks_dashboard_id, this.props.dashboardData.item_basic_data_fields]
            let itemBasicData = await this.orm.call('ks_dashboard_ninja.board', 'ks_import_item', args, kwargs)

            this.props.dashboardActions.addItem([itemBasicData])
        }
        fileReader.readAsText(this.importRef.el.files[0])
    }

    openExplainWithAI(){

        let props = this.props.dashboardActions.ksItemsCommonPropsForStructure()
        let itemsBasicData = deepCopy(props.itemsBasicData)
        props.itemsBasicData = itemsBasicData?.filter(
            (itemBasicData) => itemBasicData.ks_dashboard_item_type !== "ks_to_do"
        ) ?? props.itemsBasicData

        this.dialogService.add(KSItemsRowStructure, {
            componentInfo: {
                component: KsItems,
                props: {
                    ...props,
                    isAIExplanation: true,
                    isRowStructure: true,
                    isItemsPreview: true,
                    isGridStack: false,
                }
            }
        })

    }

    generateDashboardWithAi(){
        this.dialogService.add(FormViewDialog, {
            resModel: 'ks_dashboard_ninja.ai_dashboard',
            is_expand_icon_visible: true,   // TODO: Should be removed
            context: { 'create': false, 'ks_dashboard_id': this.ks_dashboard_id }, // TODO: context used somewhere ??
            onRecordSaved: async (record) => {
                await this.menuService.reload()
                this.notification.add(_t(" Dashboard Successfully Created "), { type: 'success' })
            },
            size: "lg",
            title: "Generate Dashboard with AI"
        })
    }

};
