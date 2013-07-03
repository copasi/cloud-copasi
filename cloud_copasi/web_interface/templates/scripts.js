function formSubmit(formName, display_loading)
{
    display_loading = typeof display_loading !== 'undefined' ? display_loading : false;
    
    if (display_loading === true) {
        $('#loading-overlay').fadeIn('slow');
        $('#loading-box').fadeIn('slow');
    }
    
    document.getElementById(formName).submit();
}
function showLoadingScreen()
{
        $('#loading-overlay').fadeIn('slow');
        $('#loading-box').fadeIn('slow');
    }
function checkResources()
{
        //Show the checking status message
    $('#checking-text').fadeIn('slow');
    //Get the status as an AJAX call
    
    $.getJSON("{% url 'api_check_resource' %}", {'user_id': "{{request.user.id}}" }, function(data){
        var bar;
        var status_text;
        if (data.status == 'unrecognized') {
            bar='warning';
            status_text = '<a href="{% url "resource_overview" %}">Warning: unrecognized AWS resources in use</a>';
        }
        else if (data.status == 'healthy'){
            bar = 'healthy';
            status_text = 'AWS status: healthy';
        }
        else if (data.status == 'problem'){
            bar = 'error';
            status_text = 'AWS status: problem';
        }                
        else if (data.status == 'pending'){
            bar = 'error';
            status_text = 'Some requested AWS resources may still be pending';
        }
        else if (data.status == 'empty'){
            bar = 'plain';
            status_text = 'No AWS resources in use';
        }
        else if (data.status == 'error'){
            bar = 'error';
            status_text = 'Error checking AWS status';
        }
        else {
            bar = 'error';
            status_text = 'Unknown status response';
        }
        var bar_name = bar + '-bar'
        var text_name = bar + '-text'
        $('#response-text').html(status_text);
        $('#response-bar').addClass(bar_name)
        $('#response-text').addClass(text_name);
        //Fade out the checking text and fade in the appropriate status bar
        $('#checking-text').fadeOut('slow', function(){
            $('#response-bar').fadeIn('slow');
            });
        });
}
window.onload = checkResources;

