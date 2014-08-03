
/*
 * Very crude way to export selected IDs from a table. Upon clicking `button`
 * this fetches all selected rows in `table`, and extracts their firsts columns
 * text. These contents are joined by '&id=' and appended to `button`.href.
 */
function exportids(form){
    form.submit(function(){
        var table = $($(this).data("table"));
        var field = $($(this).data("id-field"));
        var cancel = $(this).data("require-selection") == 1;

	var ids = $.map(table.find("tr.selected, tr.active"), function(row){
        // Select first column of row, and fetch its text (probably an ID)
        return $("td", row).first().text();
    });

	if (ids.length == 0 && cancel) {
	    //TODO: change into popover/tooltip
	    alert("Please select rows using shift or control + click");
	    return false;
	}
        $.each(ids, function(i, id){
            // For each id, create a input element
            form.get(0).appendChild(field.clone().val(id).get(0));
        });

        field.remove();
        form.find("[type=submit]").click();
    });

}
