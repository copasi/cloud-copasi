//Query the server and get any additional fields
function getExtraFormData(task_type){
    $.getJSON("{% url 'api_extra_task_fields' %}", {'task_type': task_type }, function(data){
        //Get the #formtable-extra table
        for (var i=0; i<data.fields.length; i++){
            //Add a line at the top -- only if the class is not form-group or class==selector
            
            field = data.fields[i];
            
            
            $('#formtable').append('<tr class="formrow-extra" style="display:none"><td class="topline" colspan="2"> </td></tr>')

            
            //And the row for the field
            $('#formtable').append('<tr class="formrow formrow-extra" style="display:none"><th class="fieldlabel ' + 
            field.required + '"> <label for= "' + field.id + '">' + field.label + '</label></th>' + 
            '<td class="fielddata">' + field.field + '</td></tr>');
            if (field.help_text != ' ')
            {
                $('#formtable').append('<tr class="formrow-extra" style="display:none"><td> </td><td class="fieldhelp">' + field.help_text + ' </td></tr>');
            }
            
            
            
          $('#formtable').append('<tr class="formrow-extra" style="display:none"><td class="bottomline" colspan="2"> </td></tr>');
            
        }
        $('.formrow-extra').fadeIn('slow');
        

        $('#form-submit-link').fadeIn('slow');
        $('#continue-text').hide();
        
        hide_if_not_selected();
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
    $('.hidden_form.' + class_name).parent().parent().fadeToggle('medium');
    
    $('.hidden_form.' + class_name).each(
        function()
        {
            row_class = $(this).parent().parent();
            next_row = row_class.next();
            
            console.log(next_row.find('td.bottomline').length)
            
            if (next_row.find('td.bottomline').length > 0)
            {
                row = next_row;
            }
            else if (next_row.next().find('td.bottomline').length > 0)
            {
                row = next_row.next();
            }
            else
            {
                row = next_row.next().next();
            }
            
            
            row.fadeToggle('medium');
        }
    );
    
    

}

function hide_if_not_selected()
{
    var selectors;
    selectors   = $('.selector');
    
    selectors.each(
        function()
        {
            var id = $(this).attr('id');
            //id will be of the form id_taskname
            var class_name = id.slice(3)
                        
            selector_checked = $(this).prop('checked');
            if (selector_checked != true)
            {
                $('.hidden_form.' + class_name).parent().parent().hide();
            }
        });
    
    
    //Also remove the row lines. Only bottom line if class is a selector, otherwise bottom and top lines
    
    form_groups = $('.form-group')
    
    form_groups.each(
        function()
        {
            input_class = $(this).attr('class').split(' ');
            //If this input has class form-group
            if ( input_class.indexOf('form-group') >= 0 )
            {
                //If it's not a selector, hide the topline
                if ( input_class.indexOf('selector') < 0 )
                {
                    $(this).parent().parent().prev().hide();
                }
                //Otherwise, add a space before the previous topline
                else
                {
                    $(this).parent().parent().prev().before(' <tr class="test"><td class="bottomline" colspan="2"> </td></tr>');
                }
                
                
                //For all, hide the bottom line
                //$(this).parent().parent().next().hide();
                row_class = $(this).parent().parent();
                next_row = row_class.next();
                
                console.log(next_row.find('td.bottomline').length)
                
                if (next_row.find('td.bottomline').length > 0)
                {
                    row = next_row;
                }
                else if (next_row.next().find('td.bottomline').length > 0)
                {
                    row = next_row.next();
                }
                else
                {
                    row = next_row.next().next();
                }
                
                
                row.hide();
                }
        }
    );
    
}

function select_all_selectors()
{
    $('.selector').each(function()
    {
        if ($(this).prop('checked') == false)
        {
            toggle($(this).attr('name'));
            $(this).prop('checked', true);
        }
    });
}
function deselect_all_selectors()
{
    $('.selector').each(function()
    {
        if ($(this).prop('checked') == true)
        {
            toggle($(this).attr('name'));
            $(this).prop('checked', false);
        }
    });
}

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
