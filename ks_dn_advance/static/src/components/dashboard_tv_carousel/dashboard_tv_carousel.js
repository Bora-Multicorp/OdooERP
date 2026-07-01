
import { patch } from "@web/core/utils/patch";
import { Component, onWillStart, useState ,onMounted, onWillRender, useRef, onWillPatch, onRendered, useEffect, xml  } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { isBrowserChrome, isMobileOS } from "@web/core/browser/feature_detection";
import { Ksdashboardtile } from '@ks_dashboard_ninja/components/ks_dashboard_tile_view/ks_dashboard_tile';
import { Ksdashboardtodo } from '@ks_dashboard_ninja/components/ks_dashboard_to_do_item/ks_dashboard_to_do';
import { Ksdashboardkpiview } from '@ks_dashboard_ninja/components/ks_dashboard_kpi_view/ks_dashboard_kpi';
import { Ksdashboardgraph } from '@ks_dashboard_ninja/components/ks_dashboard_graphs/ks_dashboard_graphs';
import { Dialog } from "@web/core/dialog/dialog";


/*
*   NOTE: There must be one element in carousel
*/

export class DashboardTVCarousel extends Component{

    static template = 'ks_dn_advance.dashboard_tv'

    static props = {
        componentInfo: { type: Object },
        close: { type: Function }
    }

    static components = { Dialog }

    setup(){
        this.rootRef = useRef('rootRef')
        this.isPlayPauseRef = useRef('isPlayPauseRef')
        this.isCarouselSliding = false
        this.state = useState({
            componentInfo: this.props.componentInfo,
            isPresentationMode: false,
        })

        // Note: timeInterval is in ms
        this.timeInterval = parseInt(this.state.componentInfo.props.dashboardData.ks_croessel_speed) || 3000
        onMounted(this.onMount)
    }

    onMount(){
        let carouselEl = this.rootRef.el.querySelector('.carousel')
        let carouselItemsEl = carouselEl.querySelector('.carousel-item')
        carouselItemsEl?.classList.add('active')
        this.carousel = Carousel.getOrCreateInstance(carouselEl)
        this.carousel.pause()
    }

    onNext(){
        this.carousel.next()
    }

    onPrev(){
        this.carousel.prev()
    }

    togglePresentationMode(){
        this.state.componentInfo.props.isAIExplanation = !this.state.componentInfo.props.isAIExplanation

        this.state.componentInfo.props.isColumnStructure.presentationMode =
                    this.state.isPresentationMode ? '' : 'ks-presentation-mode'

        this.state.isPresentationMode = !this.state.isPresentationMode
    }

    toggleSliding(){
        this.isCarouselSliding ? this.deleteSlidingInterval() : this.setSlidingInterval()
        this.isCarouselSliding = !this.isCarouselSliding
        this.isPlayPauseRef.el?.classList.toggle('ks-tv-play-svg-visible')
        this.isPlayPauseRef.el?.classList.toggle('ks-tv-pause-svg-visible')
    }

    setSlidingInterval(){
        this.slidingIntervalId = setInterval(() => this.carousel.next(), this.timeInterval)
    }

    deleteSlidingInterval(){
        if(this.slidingIntervalId)  clearInterval(this.slidingIntervalId)
        this.slidingIntervalId = null
    }
};