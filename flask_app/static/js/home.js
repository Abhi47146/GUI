$(document).ready(function() {

    // var somejson;
    // $.ajax({
    //     url: "http://192.168.3.164:7000/getJNdata",
    //     type: "GET",
    //     crossDomain: true,
    //     data: JSON.stringify(somejson),
    //     dataType: "json",
    //     success: function (response) {
    //         var resp = JSON.parse(response)
    //         alert(resp.status);
    //     },
    //     error: function (xhr, status) {
    //         alert("error");
    //     }
    // });
// return;
    console.log('asd')
    $('#dataTable').DataTable({
		"processing": true,
		"pageLength": 10,
		"ajax": {
			
            // 'dataType': "jsonp",
            // "async": true,
            // "crossDomain": true,
            url: "/getJNdata",
            type: 'GET',
            // crossDomain: true,
            'contentType': 'application/json',
            'accept': 'application/json',
            'dataType': "json",
			 dataSrc: '',
            
           
		},
		"columns": [
			// {
			// 	data: "Service",
			// 	render: function (data) {
			// 		return '<input type="radio" class="editor-active" name="service_id" id=' + data + ' value=' + data + '>';
			// 	},
			// 	className: "dt-body-center"
			// },
            { "data": "Junction_scn" },
            { "data": "Arm" ,  "render": function(data, type, row, meta){
                if(type === 'display'){
                    arm = meta.row +1;
                    data = '<a href="arm' + arm + '" >' + data + '</a>';
                }
    
                return data;
             } },

			{ "data": "Zone" },
            { "data": "Line_segment" },
            { "data": "Distance" },
            // { "data": "LineColourGroup",render:renderColour }
		],
		"columnDefs": [
			{
				targets: 0,
				data: null,
				defaultContent: '',
				orderable: false,
				className: 'select-checkbox text-center'
			},
			{ className: "text-center", "targets": [1] },
			{ className: "text-center", "targets": [2] },
			{ className: "text-center", "targets": [3] },
            { className: "text-center", "targets": [4] }
		],
	});

    $("submit").click(function(){
        
        window.location = "/"
    })


    // function renderData (data) {
    //     return '<input type="radio" class="editor-active" name="line_id" id=' + data + ' value=' + data + '>';
    // }

    // function renderColour (data, type, full, meta) {
    //     return `<span style="background-color: ${data}; width:136px;display:grid;/*! margin-left: 100px; *//*! margin-right: 100px; */height: 24px;align-content: center;">${data}</span>`;
    // }


});