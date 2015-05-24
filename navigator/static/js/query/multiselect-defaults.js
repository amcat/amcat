define(['jquery'], function($){
    return {
        enableFiltering: true,
        numberDisplayed: 3,
        //buttonWidth: '100%',
        enableCaseInsensitiveFiltering: true,
        onDropdownShown: function(event){
            var input = $("input.multiselect-search", event.currentTarget);
            window.setTimeout(function(){input.focus()});
        },
        disableIfEmpty: true
    };
});