
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState, useEffect, onWillUnmount, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { _t } from "@web/core/l10n/translation";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";


export class KSDashboardNinjaOverview extends Component{
    setup(){
        this.rpc = rpc
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.overviewTilesNames = [['All Dashboards', 'one'], ['All Charts', 'two'], ['Total Maps', 'three'],
                                    ['Bookmarked Dashboards', 'four'], ['All Lists', 'five']]
        this.state = useState({
            bookmarkedDashboards: false,
            filter: sessionStorage.getItem('dashboardFilter') || "All Dashboards",
        })

        onWillStart(async () => {
            this.data = await rpc("/web/dataset/call_kw/ks_dashboard_ninja.board/fetch_dashboard_overview",{
                                model: 'ks_dashboard_ninja.board',
                                method: 'fetch_dashboard_overview',
                                args: [[]],
                                kwargs:{},
                            });
            await this.env.services.menu.reload()
        })

        onWillUnmount(()=>{
            // FOR ARC Theme
            document.querySelector(".ks-zoom-view")?.classList.remove("d-none")
        })

        onMounted(()=>{
            // FOR ARC Theme
            if (document.body.classList.contains("ks_body_class")){
                document.querySelector(".ks-zoom-view")?.classList.add("d-none")
            }
        });

    }

    get isMobile(){
        return isMobileOS();
    }

    get filteredDashboards(){
        if (this.state.filter === 'Bookmarked'){
            let filteredData = Object.entries(this.data.dashboardsInfo).filter( (dashboard)=> dashboard[1].is_bookmarked);
            return filteredData.length ? Object.fromEntries(filteredData) : false;
        }
        return this.data.overviewInfo[0] ? this.data.dashboardsInfo : false;
    }

    async viewDashboard(ev){
        ev.preventDefault();
        const dashboardId = parseInt(ev.currentTarget.dataset.dashboardId)
        let clientActionId = await this.orm.silent.read(
            'ks_dashboard_ninja.board',
            [dashboardId],
            ['ks_dashboard_client_action_id']
        );
        clientActionId = clientActionId[0]?.ks_dashboard_client_action_id[0]


        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "ks_dashboard_ninja",
            params:{
                ks_dashboard_id: dashboardId
            },
            id: clientActionId
        });

    }

    onFilterChange(ev){
        this.state.filter = ev.target.text;
        this.state.bookmarkedDashboards = !this.state.bookmarkedDashboards;
        sessionStorage.setItem("dashboardFilter", this.state.filter);
        if($('#overviewFilter'))
            $('#overviewFilter').text(this.state.filter);
    }

    async updateBookmark(ev){
        let dashboardId = parseInt(ev.currentTarget.dataset.dashboardId);
        let unBookmarkSvg = $(`#unBookmark${dashboardId}`);
        let bookmarkSvg = $(`#bookmark${dashboardId}`);
        let bookmarkCountTag = $('[id="Bookmarked Dashboards"]');
        if (unBookmarkSvg && bookmarkSvg){
            unBookmarkSvg.toggleClass('d-none');
            bookmarkSvg.toggleClass('d-none');
        }
        this.data.dashboardsInfo[dashboardId].is_bookmarked = !this.data.dashboardsInfo[dashboardId].is_bookmarked;
        let updatedBookmarks = await this.rpc("/web/dataset/call_kw/ks_dashboard_ninja.board/update_bookmarks",{
                                model: 'ks_dashboard_ninja.board',
                                method: 'update_bookmarks',
                                args: [[dashboardId]],
                                kwargs:{},
                            });
        bookmarkCountTag.text(updatedBookmarks[0]);
    }

    createDashboard(ev){
        let action = {
            name: _t('Create Dashboard'),
            type: 'ir.actions.act_window',
            res_model: 'ks.dashboard.wizard',
            domain: [],
            context: {
            },
            views: [
                [false, 'form']
            ],
            view_mode: 'form',
            target: 'new',
        }
        this.actionService.doAction(action);
    }
}

KSDashboardNinjaOverview.template = "ks_dashboard_ninja.dashboardNinjaOverView";

registry.category("actions").add("dashboard_ninja", KSDashboardNinjaOverview);