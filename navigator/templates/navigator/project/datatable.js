/*
 * Display a star indicating whether this project is favourited or
 * not. This star can be clicked to change state.
 */
(function(favourite, type, row){
    if(type === "display"){
        var star = favourite ? "icon-star" : "icon-star-empty";
        var opposite = !favourite ? "icon-star" : "icon-star-empty";

        return $("<i>").addClass(star).hover(function(event){
            $(event.currentTarget).addClass(opposite);
        }, function(event){
            $(event.currentTarget).addClass(star);
        });
    }

    return favourite;
})
