requirejs.config({
    "baseUrl": AMCAT_STATIC_URL + "components",
    "urlArgs": "cache=" + CACHE_BUST_TOKEN,
    "paths": {
        "amcat": AMCAT_STATIC_URL + "js",
        "query": AMCAT_STATIC_URL + "js/query",
        "annotator": AMCAT_STATIC_URL + "js/annotator",

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
        "bootstrap-datepicker": "bootstrap-datepicker/dist/js/bootstrap-datepicker",
        "pnotify": "pnotify/pnotify.core",
        "pnotify.nonblock": "pnotify/pnotify.nonblock",
        "moment": "moment/moment",
        "renderjson": "renderjson/renderjson",
        "datatables": "datatables/media/js/jquery.dataTables",
        "datatables.tabletools": "datatables/extensions/TableTools/js/dataTables.tableTools",
        "datatables.plugins": AMCAT_STATIC_URL + "js/jquery.dataTables.plugins",
        "datatables.bootstrap": AMCAT_STATIC_URL + "js/dataTables.bootstrap",
        "jquery.cookie": "jquery-cookie/jquery.cookie",
        "jquery.highlight": AMCAT_STATIC_URL + "js/annotator/jquery.highlight",
        "jquery.scrollTo": "jquery.scrollTo/jquery.scrollTo",
        "jquery-ui": "jquery-ui/ui/jquery-ui",
        "jquery.tablednd": "TableDnD/js/jquery.tablednd.0.7.min"
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
        },
        "bootstrap":{
            deps: ['jquery']
        },
        "bootstrap-multiselect":{
            deps: ['bootstrap']
        },
        "bootstrap-datepicker":{
            deps: ['bootstrap']
        },
        "bootstrap-tooltip":{
            deps: ['bootstrap']
        },
        "renderjson":{
            exports: "renderjson"
        },
        "amcat/amcat.datatables":{
            deps: [
                'amcat/amcat',
                'datatables.plugins',
                'datatables.tabletools',
                'datatables.bootstrap',
                'jquery.cookie'
            ]
        },
        "datatables.tabletools":{
            deps: ["datatables"]
        },
        "datatables.bootstrap":{
            deps: ["datatables", "bootstrap", "jquery", "datatables.tabletools"]
        },
        "datatables.plugins":{
            deps: ["datatables", "bootstrap", "jquery"]
        },
        "datatables":{
            deps: ["jquery"]
        },
        "amcat/amcat":{
            deps: ["jquery", "bootstrap"]
        },
        "amcat/jquery.djangofields":{
            deps: ["jquery"]
        },
        "annotator/utils":{
            deps: ["jquery"]
        },
        "annotator/jquery.highlight":{
            deps: ["jquery"]
        },
        "annotator/functional":{
            deps: ["jquery"]
        },
        "jquery.hotkeys":{
            deps: ["jquery"]
        },
        "jquery.highlight":{
            deps: ["jquery"]
        },
        "jquery.scrollTo":{
            deps: ["jquery"]
        },
        "jquery-ui":{
            deps: ["jquery"]
        },
        "jquery.tablednd":{
            deps: ["jquery"]
        }
    }
});

