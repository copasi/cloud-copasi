//popup box script

$(document).ready(function () {

    // if user clicked on button, the overlay layer or the dialogbox, close the dialog  
    $('a.button-popup').click(function () {     
        $('#dialog-overlay, #dialog-box').hide();       
        return false;
    });
    
    // if user resize the window, call the same function again
    // to make sure the overlay fills the screen and dialogbox aligned to center    
    $(window).resize(function () {
        
        //only do it if the dialog box is not hidden
        if (!$('#dialog-box').is(':hidden')) popup();       
    }); 
    
    
});

//Popup dialog
function popup(message) {
        
    // get the screen height and width  
    var maskHeight = $(document).height();  
    var maskWidth = $(window).width();
    
    // calculate the values for center alignment
    var dialogTop =  (maskHeight/5) - ($('#dialog-box').height());  
    var dialogLeft = (maskWidth/3) - ($('#dialog-box').width()/3); 
    
    // assign values to the overlay and dialog box
    $('#dialog-overlay').css({height:maskHeight, width:maskWidth}).show();
    $('#dialog-box').css({top:dialogTop, left:dialogLeft}).show();
    
    // display the message
    $('#dialog-message').html(message);
            
}
