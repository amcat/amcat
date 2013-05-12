/*
 * Display a star indicating whether this project is favourited or
 * not. This star can be clicked to change state.
 */
(function(favourite, type, row){
    // Function to get icon for favourite == { true, false }
    var get_icon = function(f){ return f ? "icon-star" : "icon-star-empty"; }

    if(type === "display"){
        return $("<i>").addClass(get_icon(row.favourite)).hover(function(event){
            $(event.currentTarget).removeClass(get_icon(row.favourite)).addClass(get_icon(!row.favourite));
        }, function(event){
            $(event.currentTarget).removeClass(get_icon(!row.favourite)).addClass(get_icon(row.favourite));
        }).click(function(event){
            // We need to fetch the project url with ?star={0,1}
            row.favourite = !row.favourite;
            event.stopPropagation();

            // This script is parsed with Django templates, so we can use url.
            var url = "{% url 'project' 123 %}".replace("123", new String(row.id)) + "?star=" + (favourite ? "1" : "0");
            $.get(url).success(function(data, textStatus, jqXHR){
                row.__notify.pnotify({ hide : true, delay : 0 });
            }).error(function(data, textStatus, jqXHR){
                row.__notify.pnotify({
                    type : "error",
                    closer : true, 
                    text : "Something went wrong while (un)setting your favrouites :-(. " + 
                            "The server returned HTTP " + jqXHR.status + "."
                });
            });

            row.__notify = $.pnotify({ 
                type : "info",
                text : (row.favourite ? "Setting" : "Removing") + " project " + row.id + " as a favourite..",
                nonblock: true,
                hide: false,
                closer: false,
                sticker: false
            });
        });
    }

    return favourite;
})
