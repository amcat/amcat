define(["jquery"], function($){
    /**
     * Shamelessly stolen from: http://stackoverflow.com/a/1186309
     */
    $.fn.serializeObject = function()
    {
        var o = {};
        var a = this.serializeArray();

        $.each(a, function() {
            if (o[this.name] !== undefined) {
                if (!o[this.name].push) {
                    o[this.name] = [o[this.name]];
                }
                o[this.name].push(this.value || '');
            } else {
                o[this.name] = this.value || '';
            }
        });

        return o;
    };

    return (function serializeForm(form, sets){
        var formData = $(form).serializeObject();

        $.map($("input[type=checkbox]", form), function(input){
            var inputName = $(input).attr("name");
            formData[inputName] = input.checked;
        });

        formData["articlesets"] = sets;
        return formData;
    });
});


