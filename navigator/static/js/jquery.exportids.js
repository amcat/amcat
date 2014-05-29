
/*
 * Very crude way to export selected IDs from a table. Upon clicking `button`
 * this fetches all selected rows in `table`, and extracts their firsts columns
 * text. These contents are joined by '&id=' and appended to `button`.href.
 */
function exportids(table, button){
    button.click(function(){
        var ids = [];

        table.find(".selected").each(function(i, row){
            ids.push($("td", row).first().text());
        });

        var url = "?id=" + ids.join("&id=");
        button.attr("href", button.attr("href") + url);
    })
}