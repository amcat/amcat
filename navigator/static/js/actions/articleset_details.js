function get_selected(table){
    return table.find("tr.active").map(function(i, row){
        return row.firstChild.textContent;
    }).toArray();
}

function remove_from_set(event){
    var table = $(event.currentTarget).closest(".amcat-table-wrapper");

    $.ajax({
        "type": "POST",
        "headers": {"X-HTTP-METHOD-OVERRIDE": "DELETE"},
        "data": { "articles": get_selected(table) },
        "traditional": true
    }).done(function(){
        new PNotify({ type : "success", text: "Article(s) deleted from set." });
    }).fail(function(){
        new PNotify({ type : "error", text: "Failed to remove articles." });
    }).always(function(){
        table.find(".dataTables_scrollBody table").DataTable().draw();
    });
}

function add_to_set(event, project_id){
    var btn = $(event.currentTarget);
    var table = btn.closest(".amcat-table-wrapper");
    var modal = $(btn.data("target"));

    modal.find(".modal-title .num").text(get_selected(table).length);
    modal.find(".modal-body > p").text("Fetching available articlesets..");

    // Fetch articlesets
    $.ajax({
        type: "GET",
        url: "/api/v4/projects/" + project_id + "/articlesets/?page_size=9999&order_by=name",
        dataType: "json"
    }).success(function(data){
        var select = $("<select>");

        $.each(data.results, function(i, aset){
            var name = aset.name + " (" + aset.id + ") (" + aset.articles + " articles)";
            select.append($("<option>").prop("value", aset.id).text(name).data(aset));
        });


        // Add selector, multiselect and open filtering
        modal.find(".modal-body > p").html(select);
        select.multiselect().multiselectfilter();
        modal.find(".modal-body > p .ui-multiselect").click();
        $(".ui-multiselect-filter input[type=search]").focus();

        // Enable 'ok' button
        modal.find(".btn-primary").removeClass("disabled").click(function(){
            $(this).addClass("disabled");
            var checked = $("select").multiselect("getChecked");
            var set_ids = checked.map(function(){ return this.value; }).get();
            add_to_set_clicked(modal, get_selected(table), set_ids);
        });
    });

    modal.find(".btn-primary").addClass("disabled").off("click");
}

function add_to_set_clicked(modal, article_ids, articleset_ids){
    $.ajax({
        "type": "POST",
        "data": { "articles": article_ids, "articlesets": articleset_ids },
        "traditional": true
    }).done(function(){
        new PNotify({ type : "success", text: "Article(s) added to set(s)." });
        modal.modal("hide");
    }).fail(function(){
        new PNotify({ type : "error", text: "Failed to add articles to set." });
        modal.modal("hide");
    });
}