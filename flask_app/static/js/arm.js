var dimensions;
var line_dimensions;
$(document).ready(function () {


  // Initial state setup
  $('#drawPolygonButton, #drawLineButton').prop('disabled', true);
  $('#finishButton').prop('disabled', true);

  // Click event for Draw Polygon button
  $('#drawPolygonButton').click(function() {
      $(this).prop('disabled', true).addClass('active');
      $('#drawLineButton').prop('disabled', false).removeClass('active');
      updateFinishButtonState();
      toggleDrawingMode('polygon');
  });

  // Click event for Draw Line button
  $('#drawLineButton').click(function() {
      $(this).prop('disabled', true).addClass('active');
      $('#drawPolygonButton').prop('disabled', false).removeClass('active');
      updateFinishButtonState();
      toggleDrawingMode('line');
  });

  function updateFinishButtonState() {
      if ($('#drawLineButton').hasClass('active') || $('#drawPolygonButton').hasClass('active')) {
          $('#finishButton').prop('disabled', false).addClass('active');
      } else {
          $('#finishButton').prop('disabled', true).removeClass('active');
      }
  }

function getUrlParameter(name) {
  name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
  var regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
  var results = regex.exec(location.search);
  return results === null ? '' : decodeURIComponent(results[1].replace(/\+/g, ' '));
}

// Usage: Get the value of 'Sno' parameter from the URL
var Sno = getUrlParameter('Sno');
const submitButton = document.getElementById('submit');
    
submitButton.addEventListener('click', function() {
    // Call the getData() function when the button is clicked
    getData();
});



    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const lineCtx=canvas.getContext('2d')
    const shapes = []; // Array to store multiple shapes
    let points = []; // Array to store points for the current shape
    let line_points=[];


    let isEditing = false;
    let isDrawing = false;

    let isLineEditing = false;
    let isLineDrawing = false;

    canvas.width = 640;
    canvas.height = 640;
    // var dimensions = JSON.parse('{{ dimensions | safe }}');
    // var line_dimensions = JSON.parse('{{ line_dimensions | safe }}');



    var zone_dimensions_1 = dimensions.split(',');
    var line_segment=line_dimensions.split(',');


    // const zone_dimensions_1 = [134, 536, 508, 536, 448, 421, 168, 421];
    // const line_segment=[427, 459,126, 442];
  if(zone_dimensions_1){
    for (let i = 0; i < zone_dimensions_1.length; i += 2) {
        points.push({ x: (zone_dimensions_1[i]*640)/2560.0, y: (zone_dimensions_1[i + 1]*640)/1440.0 });
    }
    // isEditing = true;
    document.getElementById('drawPolygonButton').classList.add('active');
    document.getElementById('drawLineButton').classList.remove('active');    
    drawPolygon();
    drawMarkers();
    updateCoordinatesInputs();
  }
  if(line_segment){
    for (let i = 0; i < line_segment.length; i += 2) {
        line_points.push({ x: (line_segment[i]*640)/2560.0, y: (line_segment[i + 1]*640)/1440.0});
    }
    // isLineEditing = true;
    document.getElementById('drawPolygonButton').classList.remove('active');
    document.getElementById('drawLineButton').classList.add('active');    
    drawPolygon();
    drawMarkers();
    updateCoordinatesInputs();
  }

    function drawPolygon() {
        if (drawPolygonButton.classList.contains('active')) {
          // ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.fillStyle = 'rgba(0, 0, 255, 0.2)'; // Change the fill color to black with 50% opacity
          ctx.beginPath();

          if (points.length >= 2) {
              ctx.moveTo(points[0].x, points[0].y);
              for (let i = 1; i < points.length; i++) {
                  ctx.lineTo(points[i].x, points[i].y);
              }
          }

          if (points.length > 2) {
              ctx.lineTo(points[0].x, points[0].y);
          }

          ctx.closePath();
          ctx.fill();

          // Draw line segment if there are only two points
          if (points.length === 2) {
              ctx.strokeStyle = 'black';
              ctx.beginPath();
              ctx.moveTo(points[0].x, points[0].y);
              ctx.lineTo(points[1].x, points[1].y);
              ctx.stroke();
          }
        }
        else{

          // lineCtx.clearRect(0, 0, canvas.width, canvas.height);

          lineCtx.fillStyle = 'white';
          lineCtx.beginPath();

          if (line_points.length === 2) {
              lineCtx.strokeStyle = 'yellow';
              lineCtx.lineWidth = 3; // Set the line thickness to 3 pixels
              lineCtx.beginPath();
              lineCtx.moveTo(line_points[0].x, line_points[0].y);
              lineCtx.lineTo(line_points[1].x, line_points[1].y);
              lineCtx.stroke();
          }
        }
    }

    function drawMarkers() {

      if (drawPolygonButton.classList.contains('active')) {
        // Draw markers for polygon mode
        ctx.fillStyle = 'red';
        points.forEach(point => {
            ctx.beginPath();
            ctx.arc(point.x, point.y, 5, 0, Math.PI * 2);
            ctx.fill();
        });
    } 
    else {
        // Draw markers for line mode
        lineCtx.fillStyle = 'red';
        line_points.forEach(point => {
            lineCtx.beginPath();
            lineCtx.arc(point.x, point.y, 5, 0, Math.PI * 2);
            lineCtx.fill();
        });
    }
    }

    function updateCoordinatesInputs() {
        // Update coordinates inputs for the current shape
        if (drawPolygonButton.classList.contains('active')) {
          points.forEach((point, index) => {
              const inputVal = document.getElementById(`Coordinates_1_XY${index + 1}`);
              if (inputVal) {
                  var X_coord = (point.x * 2560) / 640.0;
                  var Y_coord = (point.y * 1440) / 640.0;                
                  inputVal.value = `${X_coord}, ${Y_coord}`;
              }
          });
        }
        else{
          line_points.forEach((point, index) => {
              const inputVal = document.getElementById(`Coordinates_1_LSXLSY${index + 1}`);
              if (inputVal) {
                var X_coord = (point.x * 2560) / 640.0;
                var Y_coord = (point.y * 1440) / 640.0;  
                inputVal.value = `${X_coord}, ${Y_coord}`;
              }
          });
        }
    }

    function finishShape() {
      
      if (drawPolygonButton.classList.contains('active') && points.length >= 4 && shapes.length < 2) {
          document.getElementById('drawPolygonButton').classList.remove('active');
            document.getElementById('drawLineButton').classList.add('active');    
            drawLineButton.disabled = false; // Make the drawLineButton inactive
            drawPolygonButton.disabled = true;
            shapes.push(points); // Finalize the current shape
            points = []; // Start a new set of points for the next shape
            isEditing = true;

        }
      else if(drawLineButton.classList.contains('active') && line_points.length>=2 && shapes.length<2){
        document.getElementById('drawPolygonButton').classList.add('active');
        document.getElementById('drawLineButton').classList.remove('active');
        drawLineButton.disabled = true; // Make the drawLineButton inactive
        drawPolygonButton.disabled = false;
        shapes.push(line_points); // Finalize the current shape
        line_points = []; // Start a new set of points for the next shape
        isLineEditing = true;
      }
    }



function toggleDrawingMode(shapeType) {
    if (shapeType=='polygon') {
            isDrawing = true;
            document.getElementById('drawPolygonButton').classList.add('active');
            document.getElementById('drawLineButton').classList.remove('active');

            // finishShape();
            // drawPolygon();
            // drawMarkers();
            // updateCoordinatesInputs();
        } else{
            isLineDrawing = true;
            document.getElementById('drawPolygonButton').classList.remove('active');
            document.getElementById('drawLineButton').classList.add('active');
            // finishShape();
            // drawPolygon();
            // drawMarkers();
            // updateCoordinatesInputs();
        }
  }



  const clearButton = document.getElementById('clearButton');
clearButton.addEventListener('click', function () {
    shapes.length = 0; // Clear all shapes
    points.length = 0; // Clear current set of points
    line_points.length=0;
    isEditing = false; // Reset editing mode
    isDrawing = false; // Reset drawing mode
    isLineEditing = false; // Reset editing mode
    isLineDrawing = false; // Reset drawing mode
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Also clear line context if needed
    lineCtx.clearRect(0, 0, canvas.width, canvas.height);

    drawPolygonButton.disabled = false; // Enable drawPolygonButton
    drawLineButton.disabled = false; // Enable drawLineButton


});

    const finishButton = document.getElementById('finishButton');
    finishButton.addEventListener('click', function () {
        finishShape(); // Finalize the current shape
    });

canvas.addEventListener('click', function (event) {
  if(drawPolygonButton.classList.contains('active')){
      if (!isDrawing) return; // Exit if not in drawing mode
      if (isEditing) return; // Exit if in editing mode
      if (points.length >= 4 || shapes.length >= 2) {
        isEditing = true;
        isDrawing= false
        return;
      }
      if (points.length === 4) return; // Allow only 4 points for polygon
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const newPoint = { x, y };
      points.push(newPoint);
      drawPolygon();
      drawMarkers();
      updateCoordinatesInputs();
    }

    else{
      if (!isLineDrawing) return; // Exit if not in drawing mode
      if (isLineEditing) return; // Exit if in editing mode
      if (line_points.length >= 2 || shapes.length >= 2) {
        isLineEditing = true;
        isLineDrawing=false
        return;
      }
      if (line_points.length === 2) return; // Allow only 2 points for line

      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const newPoint = { x, y };
      line_points.push(newPoint);
      drawPolygon();
      drawMarkers();
      updateCoordinatesInputs();
    }
});

let selectedPointIndex = -1;
let line_selectedPointIndex=-1;


canvas.addEventListener('mousedown', function (event) {


    if (drawPolygonButton.classList.contains('active')) {
        if (!isEditing) return; // Exit if not in editing mode
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        selectedPointIndex = points.findIndex(point => Math.abs(point.x - x) <= 5 && Math.abs(point.y - y) <= 5);
    } else if (drawLineButton.classList.contains('active')) {
        if (!isLineEditing) return; // Exit if not in editing mode
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        line_selectedPointIndex = line_points.findIndex(point => Math.abs(point.x - x) <= 5 && Math.abs(point.y - y) <= 5);
    }
});

canvas.addEventListener('mousemove', function (event) {
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    if (drawPolygonButton.classList.contains('active')) {
        if (!isEditing || selectedPointIndex === -1) return; // Exit if not in editing mode or no point selected

        points[selectedPointIndex] = { x, y };
        drawPolygon();
        drawMarkers();
        updateCoordinatesInputs();
    } else if (drawLineButton.classList.contains('active')) {
        if (!isLineEditing || line_selectedPointIndex === -1) return; // Exit if not in editing mode or no point selected

        line_points[line_selectedPointIndex] = { x, y };
        drawPolygon();
        drawMarkers();
        updateCoordinatesInputs();
    }
});


canvas.addEventListener('mouseup', function () {
  if (drawPolygonButton.classList.contains('active')) {
    selectedPointIndex = -1;
  }
  else
    line_selectedPointIndex = -1;
});

function getData() {

  var data = '';
  for (var i = 1; i <= 4; i++) {
    var input = document.getElementById("Coordinates_" + 1 + "_XY" + i);
    data += input.value + ',';
  }

  var line_data = '';
  for (var i = 1; i <= 2; i++) {
    var input = document.getElementById("Coordinates_1_LSXLSY" + i);
    line_data += input.value + ',';
  }
  // Remove the trailing comma
  data = data.slice(0, -1);
  line_data=line_data.slice(0,-1);

  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/update_config', true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onload = function () {
      if (xhr.status === 200) {
          // Show success message using jQuery confirm
          $.confirm({
              type: 'green',
              title: '<h3 class="text-success fw-bold mb-0">Success</h3>',
              content: '<div class="fw-bold">Coordinate update successfully</div>',
              buttons: {
                  Ok: function () {
                    var response=JSON.parse(xhr.responseText);
                    dimensions = response.dimensions;
                    line_dimensions=response.line_dimensions;

                    zone_dimensions_1 = dimensions.split(',');
                    line_segment=line_dimensions.split(',');
                
                  if(zone_dimensions_1){
                    for (let i = 0; i < zone_dimensions_1.length; i += 2) {
                        points.push({ x: parseInt(zone_dimensions_1[i]), y: parseInt(zone_dimensions_1[i + 1]) });
                    }
                    // isEditing = true;
                    document.getElementById('drawPolygonButton').classList.add('active');
                    document.getElementById('drawLineButton').classList.remove('active');    
                    drawPolygon();
                    drawMarkers();
                    updateCoordinatesInputs();
                  }
                  if(line_segment){
                    for (let i = 0; i < line_segment.length; i += 2) {
                        line_points.push({ x: parseInt(line_segment[i]), y: parseInt(line_segment[i + 1])});
                    }
                    // isLineEditing = true;
                    document.getElementById('drawPolygonButton').classList.remove('active');
                    document.getElementById('drawLineButton').classList.add('active');    
                    drawPolygon();
                    drawMarkers();
                    updateCoordinatesInputs();
                  }

                  $('#drawPolygonButton, #drawLineButton').prop('disabled', true);
                  $('#finishButton').prop('disabled', true);
              }
              }
          });
  
 
      } else {
          // Show error message using jQuery alert
          $.alert({
              type: 'red',
              title: '<h3 class="text-danger fontOpenSansBold fw-bold  mb-0">Message</h3>',
              content: '<div class="fontOpenSansRegular fw-bold ">Error updating config</div>',
          });
      }
  };
  
  // Send the request with the JSON data
  if (Sno) xhr.send(JSON.stringify({ camNumber: Sno, dimension: data, line_dimensions: line_data }));
  
  else{
    $.alert({
      type: 'red',
      title: '<h3 class="text-danger fontOpenSansBold fw-bold  mb-0">Message</h3>',
      content: '<div class="fontOpenSansRegular fw-bold ">Camera number is not assigned</div>',
    });
  }

}

});





