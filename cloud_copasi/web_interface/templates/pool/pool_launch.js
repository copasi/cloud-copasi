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
    history_line = '<tr><td class="topline" colspan="2"> </td></tr><tr class="formrow" id="spotprice-row"><th class="fieldlabel required">Spot price:</th><td id="spotprice"><div id="spotprice_current">Loading current price...</div></td><tr><td colspan="2"><div id="spotprice_history" style="width:400px; height:300px"></div></td></tr><tr><td class="bottomline" colspan="2"> </td></tr>';
    bottom_line.after(history_line);
    
    $('#spotprice_current').fadeIn();
}

function updateSpotPrice(){
    var instance_type = $('#id_initial_instance_type').val();
    var spotprice_current = $('#spotprice_current');
    spotprice_current.hide();
    spotprice_current.html('Loading...')
    spotprice_current.fadeIn();
    $.getJSON("{% url 'api_spot_price' %}", {'key_id': "{{key_id}}", 'instance_type':instance_type }, function(data){
        spotprice_current.hide();
        spotprice_current.html('$' + data['price']);
        spotprice_current.fadeIn();
    });
    
    if ( $('#id_pricing_1').attr('checked')=='checked' )
    {
        updateSpotPriceHistory();
    }
    
}

function updateSpotPriceHistory(){
    var instance_type = $('#id_initial_instance_type').val();
    //$('#spotprice_history').fadeOut();
    $.getJSON("{% url 'api_spot_price' %}", {'key_id': "{{key_id}}", 'instance_type':instance_type, 'history':true}, function(data){
        price = data['price'];

        function drawChart() {
            //var data = google.visualization.arrayToDataTable(price);
            var data = new google.visualization.DataTable();
            data.addColumn('date', 'Date');
            data.addColumn('number', 'Price');

            for (var i=0; i<price.length; i++)
            {
                data.addRows([
                    [new Date(price[i][0]), price[i][1]]
                ])
            }
            var options = {
                title: 'Price history',
                
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
        $('#spotprice_history').fadeOut();

    });
  
    $('#id_pricing_1').click(function(){ //fixed price selected
        showSpotPriceField(true);
        updateSpotPriceHistory();
    });
    
    $('#id_initial_instance_type').change(updateSpotPrice)
    showSpotPrice();
    updateSpotPrice();
}
google.load("visualization", "1", {packages:["annotatedtimeline"]});
google.setOnLoadCallback(windowLoad); //Load ajax stuff after google libs have loaded
  