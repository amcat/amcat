/**
 * http://stackoverflow.com/questions/4974238/javascript-equivalent-of-pythons-format-function
 */
String.prototype.format = function(args){
    var this_string = '';
    for (var char_pos = 0; char_pos < this.length; char_pos++) {
        this_string = this_string + this[char_pos];
    }

    for (var key in args) {
        var string_key = '{' + key + '}';
        this_string = this_string.replace(new RegExp(string_key, 'g'), args[key]);
    }
    return this_string;
};