$("[id^=chart-lines]").click(function (e) {
    var showLines = event.target.id.slice(12);
    if (showLines == "yes"){
        {% for event, data in datapts.items() %}
        myChart{{event}}.data.datasets[0].showLine = true;
        myChart{{event}}.update();
        {% endfor %} 
    } else {
        {% for event, data in datapts.items() %}
        myChart{{event}}.data.datasets[0].showLine = false;
        myChart{{event}}.update();
        {% endfor %} 

    }

});

// Adjust chart dates
$('#chart-dates').click(function(e){
    var start = $('#chart-start').val();
    //const dateRegExp = /^[0-9]{1,2}\/[0-9]{1,2}\/[0-9]{4}$/;
    const dateRegExp = /^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}$/;
    const startValid = dateRegExp.test(start);
    if (start != "" && startValid == false) {
        alert("Start date has to be in mm/dd/yyyy format");
        return
    }
    var end = $('#chart-end').val();
    const endValid = dateRegExp.test(end);
    if (end != "" && endValid == false) {
        alert("End date has to be in mm/dd/yyyy format");
        return
    }
    // refresh the page to update the charts
    //var url = "/logger/user?chart_start=" + start + "&chart_end=" + end;
    //location.href = encodeURI(url);

    // dynamically update the charts
    updateCharts(start, end);
});
$("charts-list a").on('click', function(e){
    e.preventDefault();
    $(this).tab('show');
});
// Clicking on Canvas point should bring to that day
$("[id$='Canvas']").click(function (e) {
    var chartId = e.target.id;
    var eventIdx = chartId.slice(0, -6);
    var chart = chartMap.get(eventIdx);
    var activePoint = chart.getElementsAtEvent(e)[0];
    if (activePoint !== undefined) {
        var dataset = chart.data.datasets[activePoint._datasetIndex];
        var date = dataset.data[activePoint._index].x;

        if(confirm("Would you like to go to the practice on " + date + "?")){
            var url = "/logger/search?practice_date=" + date;
            window.open(encodeURI(url));
            //location.href = encodeURI(url);

        }
    }
});

function updateCharts(start_date, end_date) {
    start = new Date(start_date);
    end = new Date(end_date);

    {% for event, data in datapts.items() %}
    var data_{{event}} = [];
    for (var j=0; j < {{ data | length }}; j++){
        data_date = new Date({{ data | safe }}[j]['x']);
        if ( data_date < start) {
            continue;
        }
        if ( data_date > end ){
            continue;
        }
        data_{{event}}.push({'x': {{ data | safe }}[j]['x'], 'y': {{ data | safe }}[j]['y']});
    }
    myChart{{event}}.data.datasets[0].data = data_{{event}};
    myChart{{event}}.update();
    {% endfor %}

}

// One scatter plot per event
const chartMap = new Map();
{% for event, data in datapts.items() %}
const ctx{{event}} = document.getElementById('{{event}}Canvas').getContext('2d');
const myChart{{event}} = new Chart(ctx{{event}}, {
    type: 'scatter',
    data: {
        datasets: [
            {
                label: '{{ event }}',
                data: [
                    {%- for datapt in data -%}
                    {x: '{{datapt.x}}', y: {{datapt.y}}}{% if not loop.last %},{% endif %}
                    {%- endfor -%}
                ],
                showLine: false,
                fill: false,
                borderColor: {%- if event.startswith("dmt") -%}'rgba(255, 99, 132, 1)'{%- else -%}'rgba(99, 99, 255, 1)'{%- endif -%},
            }
        ]
    },
    options: {
        responsive: true,
        scales: {
            xAxes: [{
                type: 'time',
                time: {
                    unit: 'day'
                }
            }]
        }
    }
});
chartMap.set('{{event}}', myChart{{event}});
{% endfor %}


// table sorting
function sortTable(f,n,t){
var s = '#'+ t +' tbody    tr';
var rows = $(s).get();

rows.sort(function(a, b) {

    var A = getVal(a);
    var B = getVal(b);

    if(A < B) {
        return -1*f;
    }
    if(A > B) {
        return 1*f;
    }
    return 0;
});

function getVal(elm){
    var v = $(elm).children('td').eq(n).text().toUpperCase();
    if($.isNumeric(v)){
        v = parseInt(v,10);
    }
    return v;
}

$.each(rows, function(index, row) {
    $('#'+t).children('tbody').append(row);
});
}
var f_sl = 1;
var f_nm = 1;
// highlight header on hover
$("[id^=col]").mouseover(function(){
$(this).css({"background-color": "lightgray", "cursor": "pointer"});
});
$("[id^=col]").mouseout(function(){
$(this).css({"background-color": "gray", "cursor": "pointer"});
});
// sort column on click
$("[id^=col]").click(function(){
    f_sl *= -1;
    table = $(this).closest("table")[0].id;
    console.log(table);
    console.log(f_sl)
    var n = $(this).prevAll().length;
    console.log(n);
    sortTable(f_sl,n, table);
});