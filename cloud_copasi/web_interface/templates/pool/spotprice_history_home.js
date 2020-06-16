function loadSpotPrice(){
    var instance_type = 'm1.medium';
    
   
    
    console.log('loading json');
     $.getJSON("{% url 'api_spot_price' %}", {'key_id': "{{key_id}}", 'instance_type':instance_type, 'history':true}, function(data){
        console.log('fading out');
        $('#spotprice_history_loadingtext').fadeOut(function(){
            $('#spotprice_history').slideDown(function(){
                price = data['price'];
        
                function drawChart() {
                    //var data = google.visualization.arrayToDataTable(price);
                    var data = new google.visualization.DataTable();
                    data.addColumn('datetime', 'Date');
                    data.addColumn('number', 'm1.medium instance price $');
        
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
            });
        });
    });
}


function windowLoad(){
    loadSpotPrice();
}
google.load("visualization", "1", {packages:["annotatedtimeline"]});
google.setOnLoadCallback(windowLoad); //Load ajax stuff after google libs have loaded
