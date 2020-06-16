function hideSpotPrice(fade){
    var spotprice_ordering = $('#id_spot_price_order_0').parent().parent().parent().parent().parent();
    
    if (fade==true){
        spotprice_ordering.fadeOut();
        spotprice_ordering.prev().fadeOut();
        spotprice_ordering.next().fadeOut();
    }
    else{
        spotprice_ordering.hide();
        spotprice_ordering.prev().hide();
        spotprice_ordering.next().hide();
    }
}

function showSpotPrice(){
    var spotprice_ordering = $('#id_spot_price_order_0').parent().parent().parent().parent().parent();
    
    spotprice_ordering.fadeIn();
    spotprice_ordering.prev().fadeIn();
    spotprice_ordering.next().fadeIn();
}

function hideSpotPriceCustom(fade){
    spotprice_custom = $('#id_spot_price_custom').parent().parent();
    if (fade == true)
    {
        spotprice_custom.fadeOut();
        spotprice_custom.prev().fadeOut();
        spotprice_custom.next().fadeOut();
    }
    else{
        console.log('hiding...')
        console.log(spotprice_custom);
        spotprice_custom.hide();
        spotprice_custom.prev().hide();
        spotprice_custom.next().hide();
        console.log('hidden')
    }
}

function showSpotPriceCustom(){
    var spotprice_custom = $('#id_spot_price_custom').parent().parent();
    spotprice_custom.fadeIn();
    spotprice_custom.prev().fadeIn();
    spotprice_custom.next().fadeIn();
}


function hideElements()
{
    if ($('#id_spot_price_order_2').attr('checked') != 'checked')
    {
        console.log('hiding spotprice order')
        hideSpotPriceCustom(false);
    }
    if ($('#id_pricing_1').attr('checked') != 'checked')
    {
        hideSpotPrice(false);
    }
    
    $('#id_pricing_1').click(function(){
        showSpotPrice();
        if ($('#id_spot_price_order_2').attr('checked') == 'checked')
        {
            showSpotPriceCustom();
        }
    });
    $('#id_pricing_0').click(function(){
        hideSpotPriceCustom(true);
        hideSpotPrice(true);
    });
    
    $('#id_spot_price_order_2').click(function(){
        showSpotPriceCustom(true);
    });
    
    $('#id_spot_price_order_1').click(function(){
        hideSpotPriceCustom(true);
    });
    
    $('#id_spot_price_order_0').click(function(){
        hideSpotPriceCustom(true);
    });

    
}
$(document).ready(function(){
    hideElements();
});

