requirejs.config({
    "baseUrl": AMCAT_STATIC_URL + "components",
    "paths": {
        "query": AMCAT_STATIC_URL + "js/query",
        "amcat": AMCAT_STATIC_URL + "js",
        "jquery": "jquery/dist/jquery",
        "jquery.hotkeys": "jquery.hotkeys/jquery.hotkeys",
        "papaparse": "papaparse/papaparse",
        "highlight": "highlight/build/highlight.pack",
        "highcharts.data": "highcharts/modules/data",
        "highcharts.exporting": "highcharts/modules/exporting",
        "highcharts.heatmap": "highcharts/modules/heatmap",
        "jquery.depends": AMCAT_STATIC_URL + "js/jquery.depends",
        "bootstrap": "bootstrap/dist/js/bootstrap",
        "bootstrap-multiselect": "bootstrap-multiselect/dist/js/bootstrap-multiselect",
        "bootstrap-tooltip": "bootstrap/js/tooltip",
        "bootstrap-datepicker": "bootstrap-datepicker/dist/js/bootstrap-datepicker"
    },
    shim:{
        "highcharts.data":{
            deps: ['highcharts/highcharts']
        },
        "highcharts.exporting":{
            deps: ['highcharts/highcharts']
        },
        "highcharts.heatmap":{
            deps: ['highcharts/highcharts']
        }
    }
});
