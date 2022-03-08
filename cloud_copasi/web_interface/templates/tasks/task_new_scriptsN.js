// -------------------------------------------------------------------------------
//  Cloud-COPASI
//  Copyright (c) 2022 Hasan Baig, Edward Kent.
//  All rights reserved. This program and the accompanying materials
//  are made available under the terms of the GNU Public License v3.0
//  which accompanies this distribution, and is available at
//  http://www.gnu.org/licenses/gpl.html
// -------------------------------------------------------------------------------

//Query the server and get any additional fields
//Query the server and get any additional fields
function getExtraFormData(task_type){
    $.getJSON("{% url 'api_extra_task_fields' %}", {'task_type': task_type }, function(data){
        //Get the #formtable-extra table

        for (var i=0; i<data.fields.length; i++){
            field = data.fields[i];
            const extraFields = document.createElement("div");
            extraFields.classList.add("form-group", "form-row", "formrow-extra")
            console.log("Field.required: ", field.required )
            console.log("Field.id: ", field.id )
            console.log("Field.label: ", field.label )
            console.log("Field.field: ", field.field )
            console.log("Field.help_text: ", field.help_text )
            console.log(" ------ ")

            // -------------
            const heading = document.createElement("div")
            heading.classList.add("col-sm-3", "col-md-3", "col-lg-3", "col-xl-3", "col-xs-3")
            const label = document.createElement("label")
            const id = label.htmlFor
            label.htmlFor = field.id
            label.innerHTML = field.label
            heading.append(label)

            const parameter = document.createElement("div")
            parameter.classList.add("col-sm-9", "col-md-9", "col-lg-9", "col-xl-9", "col-xs-9")
            parameter.innerHTML = field.field

            const helpText = document.createElement("div")
            helpText.classList.add("form-text", "text-muted")
            helpText.innerHTML = field.help_text
            parameter.append(helpText)

            if (field.label === "Algorithms" |
                field.label === "Current Solution Statistics" |
                field.label === "Genetic Algorithm" |
                field.label === "Genetic Algorithm SR" |
                field.label === "Hooke & Jeeves" |
                field.label === "Lavenberg-Marquardt" |
                field.label === "Evolutionary Programming" |
                field.label === "Random Search" |
                field.label === "Nelder-Mead" |
                field.label === "Particle Swarm" |
                field.label === "Praxis" |
                field.label === "Truncated Newton" |
                field.label === "Simulated Annealing" |
                field.label === "Evolution Strategy" |
                field.label === "Steepest Descent")
                {
                heading.style = "font-weight:bold"
                }
                else{
                  heading.style.fontStyle = "italic"
                }

            extraFields.append(heading)
            extraFields.append(parameter)
            //
            const formtableClass = document.querySelector("#formtable")
            formtable.append(extraFields)

        }

        $('.formrow-extra').fadeIn('slow');


        $('#form-submit-link').fadeIn('slow');
        $('#continue-text').hide();

        // hide_if_not_selected();
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
                $('.hidden_form.' + class_name).hide();
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
                   //$(this).parent().parent().prev().before(' <tr class="test"><td class="bottomline" colspan="2"> </td></tr>');
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

   // hide_if_not_selected();

})
