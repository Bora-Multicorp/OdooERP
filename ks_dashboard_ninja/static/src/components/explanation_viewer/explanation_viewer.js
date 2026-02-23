
import { Component, useState, onMounted, onWillUnmount, useRef, status } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useForwardCbToParent } from '@ks_dashboard_ninja/js/access_utils';
import { _t } from "@web/core/l10n/translation";
import { useBus } from "@web/core/utils/hooks";


export class ExplanationViewer extends Component {
    static template = "ks_dashboard_ninja.explanation_viewer"
    static props = {
        itemConfig: { type: [Object, Boolean] },
        listViewConfig: { type: [Object, Boolean], optional: true },
        chartConfig: { type: [Object, Boolean], optional: true },
        explanationText: { type: String , optional: true },
        fetchExplanation: { type: Function , optional: true }
    }

    setup(){

        this.state = useState({
            explanation: this.props.explanationText || false,
            isPlay: false,
        })
        this.audioRef = useRef("audioRef")

        onMounted( () => this.audioRef.el.addEventListener('ended', this.onAudioEnded.bind(this)))
        onWillUnmount( () => this.audioRef.el.removeEventListener('ended', this.onAudioEnded.bind(this)))

        useBus(this.env.bus, 'DN: Pause All', ({ detail }) => {
            this.audioRef.el.pause()
            if(detail.itemId != this.props.itemConfig.id){
                this.state.isPlay = false
            }
        })


        this.fetchExplanation = useForwardCbToParent('fetchExplanation')
        this.orm = useService('orm')
        this.notification = useService('notification')
    }

    async fetchExplanation(){
        // FIXME: ks_generate_analysis should be improved , flow for the explanation analysis should be improved

        const config = {
            ...this.props.itemConfig,
            ks_chart_data: { ...this.props.chartConfig },
            ks_list_view_data: { ...this.props.listViewConfig },
        }
        let args = [[config], [], this.props.itemConfig.ks_dashboard_id]
        let explanation = await this.orm.call('ks_dashboard_ninja.arti_int', 'ks_generate_analysis', args)
        // TODO: change approach , use of useChildCb bind this component this to parent , preventing Garbage collection, giving error - component destroyed

        this.state.explanation = explanation
    }

    onAudioEnded(){
        this.state.isPlay = false
    }


    async speakText(){

        this.env.bus.trigger('DN: Pause All', { itemId: this.props.itemConfig.id })

        if(this.state.explanation === ''){
            this.notification.add(_t("No explanation present"), { type: 'warning' })
            return
        }

        this.state.isPlay = !this.state.isPlay

        if(this.audioRef.el.src === ''){
            let audio = await this.orm.call('ks_dashboard_ninja.arti_int', 'convert_tts', [[], this.state.explanation], {})
            this.audioRef.el.src = "data:audio/wav;base64, " + audio.snd

            if(audio.error){
                this.notification.add(_t(audio.message), { type: 'warning' })
                return
            }

        }

        if(this.state.isPlay){
            this.audioRef.el.play()
            return;
        }

        this.audioRef.el.pause()
    }
}





