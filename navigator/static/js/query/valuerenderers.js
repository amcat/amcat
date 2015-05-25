define(["moment"], function(moment){
    return {
        "medium": function(medium){
            return medium.id + " - " + medium.label;
        },
        "set": function(articleset){
            return articleset.id + " - " + articleset.label;
        },
        "date": function(date){
            return moment(date).format("DD-MM-YYYY");
        },
        "total": function(total){
            return "Total";
        },
        "term": function(term){
            return term.id;
        }
    };
});