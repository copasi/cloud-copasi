//Query the server and get any additional fields
function getExtraFormData(task_type){
    
    $.getJSON("{% url 'api_extra_task_fields' %}", {'task_type': task_type }, function(data){
        //Get the #formtable-extra table
        for (var i=0; i<data.fields.length; i++){
            
            $('#formtable').append('<tr class="formrow-extra" style="display:none"><td class="topline" colspan="2"> </td></tr>')
            
            field = data.fields[i];
            $('#formtable').append('<tr class="formrow formrow-extra" style="display:none"><th class="fieldlabel ' + 
            field.reqired + '"> <label for= "' + field.id + '">' + field.label + '</label></th>' + 
            '<td class="fielddata">' + field.field + '</td></tr>');
            if (field.help_text != ' ')
            {
                $('#formtable').append('<tr class="formrow-extra" style="display:none"><td> </td><td class="fieldhelp">' + field.help_text + ' </td></tr>')
            }
        }
        $('.formrow-extra').fadeIn('slow')
        $('#form-submit-link').fadeIn('slow')
    });
}
//Remove any extra fields that have been added
function clearExtraFormData(){
    $('.formrow-extra').fadeOut('slow', function(){$('.formrow-extra').remove();});
    $('#form-submit-link').fadeOut('slow')
}

//bind the task type change event
$(document).ready(function() {
    $('#id_task_type').change(function(){
        clearExtraFormData();
        if ($('#id_task_type').val() != ''){
            getExtraFormData($('#id_task_type').val());
        } 
    });
});

$(document).ready(function(){
    //Hide the submit button
    if ($('#id_task_type').val() == ''){
        $('#form-submit-link').hide();
    }
})
