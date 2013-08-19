//Query the server and get any additional fields
function getExtraFormData(task_type){
    $.getJSON("{% url 'api_extra_task_fields' %}", {'task_type': task_type }, function(data){
        //Get the #formtable-extra table
        for (var i=0; i<data.fields.length; i++){
            //Add a line at the top
            $('#formtable').append('<tr class="formrow-extra" style="display:none"><td class="topline" colspan="2"> </td></tr>')
            //And the row for the field
            field = data.fields[i];
            $('#formtable').append('<tr class="formrow formrow-extra" style="display:none"><th class="fieldlabel ' + 
            field.required + '"> <label for= "' + field.id + '">' + field.label + '</label></th>' + 
            '<td class="fielddata">' + field.field + '</td></tr>');
            if (field.help_text != ' ')
            {
                $('#formtable').append('<tr class="formrow-extra" style="display:none"><td> </td><td class="fieldhelp">' + field.help_text + ' </td></tr>');
            }
        }
        $('.formrow-extra').fadeIn('slow');
        
        //Hide again if class is hidden
        $('.hidden_form').parent().parent().hide();
        $('.hidden_form').parent().parent().next().hide();

        $('#form-submit-link').fadeIn('slow');
        $('#continue-text').hide();
    });
}
//Remove any extra fields that have been added
function clearExtraFormData(next_task){
    
    if ($('.formrow-extra').length > 0){
        $('#form-submit-link').fadeOut('slow');
        //Use promise.done construct so that callback is only performed once
        $('.formrow-extra').fadeOut('slow').promise().done(function(){
            $('.formrow-extra').remove();
            if (next_task != ''){
                getExtraFormData(next_task);
            }
            else{
                $('#continue-text').fadeIn('slow');
            }
        });
    }
    else {
        if (next_task != ''){
                getExtraFormData(next_task);
            }
        else {
            $('#continue-text').fadeIn('slow');
            $('#form-submit-link').hide();
        }
    }
}


function toggle(class_name)
{
    $('.hidden_form.' + class_name).parent().parent().fadeToggle('slow');
    $('.hidden_form.' + class_name).parent().parent().next().fadeToggle('slow');
}

function hide_if_not_selected()
{
    var selectors;
    selectors   = $('.selector');
    
    selectors.each(
        function()
        {
            var id = $(this).attr('id');
            //id will be of the form id_somename_enabled
            var name = id.slice(2, 8)
            console.log(name)
            
            selector_checked = $('this : checked').length > 0;
    
            if (selector_checked != true)
            {
                $('.hidden_form.' + class_name).parent().parent().hide();
                $('.hidden_form.' + class_name).parent().parent().next().hide();
            }
    
}

        }
    );
    

//bind the task type change event
$(document).ready(function() {
    $('#id_task_type').change(function(){
        clearExtraFormData($('#id_task_type').val())
    });
});

$(document).ready(function(){
    //Hide the submit button
    if ($('#id_task_type').val() == ''){
        $('#form-submit-link').hide();
        //Add some text after the form
        $('<span class="bold" id="continue-text">Select a task type to continue</span>').insertAfter('#formtable');
    }
    else{
        //If a task type is already selected, disable the choice to chainge it since it will not load properly
        $('#id_task_type').prop('disabled', true);
    }
    
    //Hide any non-selected form elements if they have class hidden-form
    
    hide_if_not_selected();
    
})
