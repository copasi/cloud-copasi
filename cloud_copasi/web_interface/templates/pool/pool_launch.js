var input_row;
var help_text_row;
var bottom_line;
var top_line;

function hideSpotPriceField(){
    input_row.hide();
    help_text_row.hide();
    bottom_line.hide();
    top_line.hide();
}
function showSpotPriceField(){
    //Always slide
    input_row.fadeIn();
    help_text_row.fadeIn();
    bottom_line.fadeIn();
    top_line.fadeIn();
}

function showSpotPrice(){
    //Insert a field after bottom_line
    history_line = '<tr><td class="topline" colspan="2"> </td></tr>\
    <tr class="formrow" id="spotprice-row"><th class="fieldlabel required">Current spot price:</th>\
        <td id="spotprice"><div id="spotprice_current">Loading current price...</div></td>\
    </tr>\
    <tr id="spotprice_history_row" style="height:300px"><th class="fieldlabel required" style="vertical-align:middle;">Spot price history:</th><td><div id="spotprice_history" style="width:600px; height:300px"></div></td></tr>\
    <tr><td class="bottomline" colspan="2"> </td></tr>';
    bottom_line.after(history_line);
    
    $('#spotprice_current').fadeIn();
}

function updateSpotPrice(){
    var instance_type = $('#id_initial_instance_type').val();
    var spotprice_current = $('#spotprice_current');
    spotprice_current.hide();
    spotprice_current.html('Loading current price...')
    spotprice_current.fadeIn();
    $.getJSON("{% url 'api_spot_price' %}", {'key_id': "{{key_id}}", 'instance_type':instance_type }, function(data){
        spotprice_current.hide();
        spotprice_current.html('$' + data['price'] + '  (' + instance_type + ')');
        spotprice_current.fadeIn();
    });
    
    if ( $('#id_pricing_1').attr('checked')=='checked' )
    {
        updateSpotPriceHistory();
    }
    else
    {
        $('#spotprice_history_row').hide()
    }
    
}

function updateSpotPriceHistory(){
    var instance_type = $('#id_initial_instance_type').val();
    $('#spotprice_history_row').fadeOut();
    $('#spotprice_history').html('');
    $('#spotprice_history').html('<div style="height:300px; line-height:300px"><span style="line-height:normal; vertical-align: middle">Loading price history...</span></div>');
    $('#spotprice_history_row').fadeIn();

    $.getJSON("{% url 'api_spot_price' %}", {'key_id': "{{key_id}}", 'instance_type':instance_type, 'history':true}, function(data){
        price = data['price'];

        function drawChart() {
            //var data = google.visualization.arrayToDataTable(price);
            var data = new google.visualization.DataTable();
            data.addColumn('datetime', 'Date');
            data.addColumn('number', 'Price $');

            for (var i=0; i<price.length; i++)
            {
                data.addRows([
                    [new Date(price[i][0]), price[i][1]]
                ])
            }
            var options = {
                title: 'Price history',
                displayExactValues: true,
                displayZoomButtons: false,
                scaleType : 'maximized',
                
                
            };

            var chart = new google.visualization.AnnotatedTimeLine(document.getElementById('spotprice_history'));
            chart.draw(data, options);
        }
      
        drawChart();
        
        //$('#spotprice_history').fadeIn();
    });
}

function windowLoad(){
    input_row = $('#id_spot_bid_price').parent().parent();
    help_text_row = input_row.next();
    bottom_line = help_text_row.next();
    top_line = input_row.prev();

    
    if ($('#id_pricing_0').attr('checked') == 'checked'){
        hideSpotPriceField();
    }
    else
    {
        updateSpotPriceHistory();
    }
    $('#id_pricing_0').click(function(){ //fixed price selected
        hideSpotPriceField(true);
        $('#spotprice_history_row').fadeOut();

    });
  
    $('#id_pricing_1').click(function(){ //fixed price selected
        showSpotPriceField(true);
        updateSpotPriceHistory();
    });
    
    $('#id_initial_instance_type').change(updateSpotPrice);
    showSpotPrice();
    updateSpotPrice();
}
google.load("visualization", "1", {packages:["annotatedtimeline"]});
google.setOnLoadCallback(windowLoad); //Load ajax stuff after google libs have loaded
  