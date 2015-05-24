_Poll = (function($, uuid, opts){
    var nop = function(){};

    // Statuses (stati? :-))
    var STATUS = {
        INPROGRESS: "INPROGRESS",
        SUCCESS: "SUCCESS",
        FAILED: "FAILURE"
    };

    // Initial timeout in milliseconds. Will increase half a second for
    // every poll, with an upper limit of 3 seconds.
    var timeout_max = 3000;
    var timeout = 200;
    var step = 500;

    var done_callback = nop;
    var fail_callback = nop;
    var result_callback = nop;
    var progress_callback = nop;
    var task_fail_callback = nop;
    var always_callback = nop;

    // Trust server to return attachment header?
    var download = opts.download | false;

    var TASK_API = "/api/v4/task?uuid=" + uuid + "&format=json";
    var RESULT_API = "/api/v4/taskresult/" + uuid + "?format=json";

    function poll(){
        $.get(TASK_API).done(_poll_done).fail(_poll_fail);
        return this;
    }

    function bump_timeout(){
        return timeout += (timeout > timeout_max) ? 0 : step;
    }

    /**
     * Defines which function should be called after a task was succesfully
     * completed server-side.
     *
     * @param callback function(data, textStatus, jqXHR)
     */
    function done(callback){
        done_callback = callback;
        return this;
    }

    /**
     * Defines which function should be called after an fail occured either
     * while polling or while processing results server-side.
     *
     * @param callback function(jqXHR, textStatus, errorThrown)
     */
    function fail(callback){
        fail_callback = callback;
        return this;
    }

    /**
     * Defines which function should be called after a task has finished
     * donefully server-side, and the result has been fetched.
     *
     * @param callback function(data, textStatus, jqXHR)
     */
    function result(callback){
        result_callback = callback;
        return this;
    }

    /**
     * Defines which function should be called after each poll. Can be
     * used to display a progress bar.
     *
     * @param callback function(progress, message)
     */
    function progress(callback){
        progress_callback = callback;
        return this;
    }

    /**
     * Defines which function should be called if task failed server-side.
     *
     * @param callback function(api_error)
     */
    function task_fail(callback){
        task_fail_callback = callback;
        return this;
    }

    /**
     * Defines which function should always be called, even at failure.
     *
     * @param callback function()
     */
    function always(callback){
        always_callback = callback;
        return this;
    }

    /**
     *
     *
     * @param message_element
     * @param progress_bar
     */
    function progress_bar(message_element, progress_bar){
        progress(function(completed, message){
            message_element.text(message);
            progress_bar.css("width", completed + "%");
        });
    }

    function _poll_done(data, textStatus, jqXHR){
        var task = data.results[0];

        if (task.ready){
            if (task.status === STATUS.SUCCESS){
                if (download){
                    window.location = RESULT_API;
                    always_callback();
                } else {
                    $.ajax(RESULT_API).done(_result_done).fail(_result_fail);
                }

            } else if(task.status === STATUS.FAILED){
                _result_fail(data, textStatus, jqXHR);
            } else {
                throw "Unknown status code: " + task.status;
            }

            return;
        }

        // Check for progress and callback
        if (task.progress !== null){
            progress_callback(
                task.progress.completed,
                task.progress.message
            );
        }

        // Pol again in a while
        window.setTimeout(poll, bump_timeout());
    }

    function _poll_fail(jqXHR, textStatus, errorThrown){
        fail_callback(jqXHR, textStatus, errorThrown);
        always_callback();
    }

    function _result_fail(data, textStatus, jqXHR){
        fail_callback(data, textStatus, jqXHR);
        always_callback();
    }

    function _result_done(data, textStatus, jqXHR){
        result_callback(data, textStatus, jqXHR);
        always_callback();
    }

    // Go!
    poll();

    // Public functions
    this.always = always;
    this.done = done;
    this.fail = fail;
    this.result = result;
    this.progress = progress;
    this.progress_bar = progress_bar;
    return this;
});

/**
 * Serves as an javascript API for the Task API. Example usage:
 *
 * >>> Poll(uuid, options).result(function(data, status, jqXHR){
 * >>>     alert("Succesfully fetched task result!");
 * >>> });
 */
define(["jquery"], function($){
    console.log($)
    return function(uuid, opts){
        return _Poll.call({}, $, uuid, opts === undefined ? {} : opts);
    }
});
