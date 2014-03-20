/*
 * Display a star indicating whether this project is favourited or
 * not. This star can be clicked to change state.
 */
(function(favourite, type, row){
    // Function to get icon for favourite == { true, false }
    var get_icon = function(f){ return f ? "glyphicon-star" : "glyphicon-star-empty"; }

    if(type === "display"){
        return $("<i class='glyphicon'>").addClass(get_icon(row.favourite)).hover(function(event){
            $(event.currentTarget).removeClass(get_icon(row.favourite)).addClass(get_icon(!row.favourite));
        }, function(event){
            $(event.currentTarget).removeClass(get_icon(!row.favourite)).addClass(get_icon(row.favourite));
        }).click(function(event){
            // We need to fetch the project url with ?star={0,1}
            row.favourite = !row.favourite;
            event.stopPropagation();

	    // get the url from the template, and customize by replacing 123 -> row.id
	    var url = row.favourite ? "{{ set_url }}" : "{{ unset_url }}";
	    var url = url.replace("123", new String(row.id))

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
                text : (row.favourite ? "Setting" : "Removing") + " {{ label }} " + row.id + " as a favourite..",
                nonblock: true,
                hide: false,
                closer: false,
                sticker: false
            });
        });
    }

    return favourite;
})
