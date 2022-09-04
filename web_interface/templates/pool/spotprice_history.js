function updateSpotPrice(){
    var instance_type = $('#id_instance_type').val();
    
    var spotprice_current = $('#spotprice_current');
    spotprice_current.hide();
    spotprice_current.html('Loading current price...')
    spotprice_current.fadeIn();
    $.getJSON("{% url 'api_spot_price' %}", {'key_id': "{{key_id}}", 'instance_type':instance_type }, function(data){
        spotprice_current.hide();
        spotprice_current.html('$' + data['price'] + '  (' + instance_type + ')');
        spotprice_current.fadeIn();
    });
    
    $('#spotprice_history').fadeOut();
    $('#spotprice_history').html('');
    $('#spotprice_history').html('<div style="height:300px; line-height:300px"><span style="line-height:normal; vertical-align: middle">Loading price history...</span></div>');
    $('#spotprice_history').fadeIn();
    console.log("hello")
    $.getJSON("{% url 'api_spot_price' %}", {'key_id': "{{key_id}}", 'instance_type':instance_type, 'history':true}, function(data){
        price = data['price'];

        function drawChart() {
            var data = new google.visualization.DataTable();
            data.addColumn('datetime', 'Date');
            data.addColumn('number', 'Price $');

            for (var i=0; i<price.length; i++)
            {
                data.addRows([
                    [new Date(price[i][0]),{f:price[i][1]}]
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
        }*/
        //console.log(price)    
        //drawChart();
        
    });
}


function windowLoad(){
    $('#id_instance_type').change(updateSpotPrice);
    updateSpotPrice();
}
google.load("visualization", "1", {packages:["annotatedtimeline"]});
google.setOnLoadCallback(windowLoad); //Load ajax stuff after google libs have loaded
