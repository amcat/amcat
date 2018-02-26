

define(["jquery", "annotator/annotator", "amcat/amcat.datatables"], function($, annotator){
    var jqueryElement = $('[data-datatable]');
    var url = jqueryElement.data("datatable-src");
    var columns = [], column_order = [
        "id", "article_id", "title", "medium", "date", "pagenr",
        "length", "status", "comments"
    ];

    var sortable = [
        "id", "title", "comments", "article_id", "medium", "date",
        "pagenr", "length", "status"
    ];

    columns = $.map(column_order, function(colname){
        return {
            bSortable: sortable.indexOf(colname) !== -1,
            mData : colname, aTargets : [colname]
        };
    });

    amcat.datatables.create_rest_table(jqueryElement, url, {
        datatables_options: {
            aaSorting: [[0, "asc"]],
            iDisplayLength: 100000,
            //aoColumns: columns,
            sScrollY: "100px",
            searching: false,

            fnDrawCallback: function(){
                $("tr", $("#article-table-container")).click(function(event){
                    annotator.datatables_row_clicked($(event.currentTarget));
                }).css("cursor", "pointer");
            }
        },
        setup_callback: function(tbl){
            console.log("Done setting up datatable..");
            annotator.datatable = tbl;
        }
    });
    return null;
});