import os
import urllib.request
from flask import Flask, flash, request, redirect, url_for, render_template, Response
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from configparser import ConfigParser

app = Flask(__name__)

parser = ConfigParser()
configfile = "configfile.ini"
parser.read(configfile)
junction_scn = parser.get('DEFAULT','JUNCTION_SCN')
arms = parser.get('DEFAULT','ARM_IDS',fallback="")
if arms != "":
    arms = arms.split(",")
armslen = len(arms)
stream = []
ja = []
armsp = ''
for arm in arms:
    ja.append({'Junction_scn':junction_scn,'Arm':arm,'Zone':'0,0,0,0,0,0,0,0','Line_segment':'0,0,0,0','Distance':'0'})
    st = parser.get(arm,'STREAM')
    stream.append(st)
    armsp = arm + '_SPEED'
    try:
        parser.add_section(armsp)
        print(armsp)
        parser.set(armsp, 'line_segment_coordinates', '')
        parser.set(armsp, 'distance', '')
    except:
        parser.set(armsp, 'line_segment_coordinates', '')
        parser.set(armsp, 'distance', '')
with open('configfile.ini', 'w') as configfile:
    parser.write(configfile)
print(ja)
#camera = cv2.VideoCapture('/home/itspe/Videos/J091_L01/WhatsApp Video 2022-12-15 at 10.57.22 AM.mp4')  # use 0 for web camera
#  for cctv camera use rtsp://username:password@ip_address:554/user=username_password='password'_channel=channel_number_stream=0.sdp' instead of camera
# for local webcam use cv2.VideoCapture(0)
coordinates_1 = '0,0,0,0,0,0,0,0'
coordinates_2 = '0,0,0,0,0,0,0,0'
coordinates_3 = '0,0,0,0,0,0,0,0'
coordinates_4 = '0,0,0,0,0,0,0,0'
lsv_1 = '0,0,0,0'
lsv_2 = '0,0,0,0'
lsv_3 = '0,0,0,0'
lsv_4 = '0,0,0,0'
st_1 = junction_scn + ' Arm_1 Zone Coordinates'
st_2 = junction_scn + ' Arm_2 Zone Coordinates'
st_3 = junction_scn + ' Arm_3 Zone Coordinates'
st_4 = junction_scn + ' Arm_4 Zone Coordinates'
ls_1 = junction_scn + ' Arm_1 Line Segment'
ls_2 = junction_scn + ' Arm_2 Line Segment'
ls_3 = junction_scn + ' Arm_3 Line Segment'
ls_4 = junction_scn + ' Arm_4 Line Segment'

form_data = {
    st_1:'',
    ls_1:'',
    st_2:'',
    ls_2:'',
    st_3:'',
    ls_3:'',
    st_4:'',
    ls_4:'',
}



def check_coordinates(cd,st,coordinates,form_data,lcd,lsv,lst,num,dis):
    if(cd!=',,,,,,,'):
        try:
            t = len(list(map(int,cd.split(","))))
            if(t==8):
                coordinates = cd
                form_data[st] = coordinates
                ja[num]['Zone'] = coordinates
        except:
            coordinates = coordinates
    if(lcd!=',,,'):
        try:
            t = len(list(map(int,lcd.split(","))))
            if(t==4):
                lsv = lcd
                form_data[lst] = lsv
                ja[num]['Line_segment'] = lsv
        except:
            lsv = lsv
    if(dis!=''):
        ja[num]['Distance'] = dis
        
    
    return ja[num]['Zone'],ja[num]['Line_segment'],ja[num]['Distance']

def gen_frames(camera,coordinates,line_coordinates):  # generate frame by frame from camera
    while True:
        # Capture frame-by-frame
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            frame = cv2.resize(frame,(640,640))
            dim_list = [[0,0],[0,0],[0,0], [0,0]]
            start_point = (0,0)
            end_point = (0,0)
            if(coordinates!=''):
                cord = list(map(int,coordinates.split(",")))
                dim_list = [[cord[0],cord[1]],[cord[2],cord[3]],[cord[4],cord[5]], [cord[6],cord[7]]]
            if(line_coordinates!=''):
                lc = list(map(int,line_coordinates.split(',')))
                start_point = (lc[0],lc[1])
                end_point = (lc[2],lc[3])
            pts = np.array(dim_list,
               np.int32)
            frame = cv2.line(frame, start_point, end_point, (255,0,0), 2)
            frame = cv2.polylines(frame, [pts] ,True, (255,0,0), 2)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result


@app.route('/arm1/video_feed')
def video_feed_1():
    #Video streaming route. Put this in the src attribute of an img tag
    if(armslen>=1):
        camera = cv2.VideoCapture(stream[0])
        coordinates_1 = form_data.get(st_1)
        lsv_1 = form_data.get(ls_1)
        return Response(gen_frames(camera,coordinates_1,lsv_1), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(request.url)

@app.route('/arm2/video_feed')
def video_feed_2():
    #Video streaming route. Put this in the src attribute of an img tag
    if(armslen>=2):
        camera = cv2.VideoCapture(stream[1])
        coordinates_2 = form_data.get(st_2)
        lsv_2 = form_data.get(ls_2)
        return Response(gen_frames(camera,coordinates_2,lsv_2), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(request.url)

@app.route('/arm3/video_feed')
def video_feed_3():
    #Video streaming route. Put this in the src attribute of an img tag
    if(armslen>=3):
        camera = cv2.VideoCapture(stream[2])
        coordinates_3 = form_data.get(st_3)
        lsv_3 = form_data.get(ls_3)
        return Response(gen_frames(camera,coordinates_3,lsv_3), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(request.url)

@app.route('/arm4/video_feed')
def video_feed_4():
    #Video streaming route. Put this in the src attribute of an img tag
    if(armslen>=4):
        camera = cv2.VideoCapture(stream[3])
        coordinates_4 = form_data.get(st_4)
        lsv_4 = form_data.get(ls_4)
        return Response(gen_frames(camera,coordinates_4,lsv_4), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(request.url)



@app.route('/arm1', methods=['POST'])
def upload_cord_1():
    global coordinates_1
    global lsv_1
    num = 0
    cd = ''
    cdx = 'Coordinates_1_XY'
    lcd = ''
    lcdx = 'Coordinates_1_LSXLSY'
    for j in range(1,5):
        if(j!=4):
            cd = cd + str(request.form.get(cdx + str(j),default=0)) + ','
        else:
            cd = cd + str(request.form.get(cdx + str(j),default=0))
    for j in range(1,3):
        if(j!=2):
            lcd = lcd + str(request.form.get(lcdx + str(j),default=0)) + ','
        else:
            lcd = lcd + str(request.form.get(lcdx + str(j),default=0))
    dis = str(request.form.get('dis',default='0'))
    a,b,c = check_coordinates(cd,st_1,coordinates_1,form_data,lcd,lsv_1,ls_1,0,dis)
    parser = ConfigParser()
    configfile = "configfile.ini"
    parser.read(configfile)
    parser.set(ja[num]['Arm'],'zone_dimensions_1',a)
    parser.set(ja[num]['Arm'] + '_SPEED', 'line_segment_coordinates_1', b)
    parser.set(ja[num]['Arm'] + '_SPEED', 'distance_1', c)
    with open('configfile.ini', 'w') as configfile:
        parser.write(configfile)
    return redirect(request.url)

@app.route('/arm2', methods=['POST'])
def upload_cord_2():
    global coordinates_2
    global lsv_2
    num = 1
    cd = ''
    cdx = 'Coordinates_2_XY'
    lcd = ''
    lcdx = 'Coordinates_2_LSXLSY'
    for j in range(1,5):
        if(j!=4):
            cd = cd + str(request.form.get(cdx + str(j),default=0)) + ','
        else:
            cd = cd + str(request.form.get(cdx + str(j),default=0))
    for j in range(1,3):
        if(j!=2):
            lcd = lcd + str(request.form.get(lcdx + str(j),default=0)) + ','
        else:
            lcd = lcd + str(request.form.get(lcdx + str(j),default=0))
    dis = str(request.form.get('dis',default='0'))
    a,b,c = check_coordinates(cd,st_2,coordinates_2,form_data,lcd,lsv_2,ls_2,1,dis)
    parser = ConfigParser()
    configfile = "configfile.ini"
    parser.read(configfile)
    parser.set(ja[num]['Arm'],'zone_dimensions_1',a)
    parser.set(ja[num]['Arm'] + '_SPEED', 'line_segment_coordinates_1', b)
    parser.set(ja[num]['Arm'] + '_SPEED', 'distance_1', c)
    with open('configfile.ini', 'w') as configfile:
        parser.write(configfile)
    return redirect(request.url)

@app.route('/arm3', methods=['POST'])
def upload_cord_3():
    global coordinates_3
    global lsv_3
    num = 2
    cd = ''
    cdx = 'Coordinates_3_XY'
    lcd = ''
    lcdx = 'Coordinates_3_LSXLSY'
    for j in range(1,5):
        if(j!=4):
            cd = cd + str(request.form.get(cdx + str(j),default=0)) + ','
        else:
            cd = cd + str(request.form.get(cdx + str(j),default=0))
    for j in range(1,3):
        if(j!=2):
            lcd = lcd + str(request.form.get(lcdx + str(j),default=0)) + ','
        else:
            lcd = lcd + str(request.form.get(lcdx + str(j),default=0))
    dis = str(request.form.get('dis',default='0'))
    a,b,c = check_coordinates(cd,st_3,coordinates_3,form_data,lcd,lsv_3,ls_3,2,dis)
    parser = ConfigParser()
    configfile = "configfile.ini"
    parser.read(configfile)
    parser.set(ja[num]['Arm'],'zone_dimensions_1',a)
    parser.set(ja[num]['Arm'] + '_SPEED', 'line_segment_coordinates_1', b)
    parser.set(ja[num]['Arm'] + '_SPEED', 'distance_1', c)
    with open('configfile.ini', 'w') as configfile:
        parser.write(configfile)
    return redirect(request.url)

@app.route('/arm4', methods=['POST'])
def upload_cord_4():
    global coordinates_4
    global lsv_4
    num = 3
    cd = ''
    cdx = 'Coordinates_4_XY'
    lcd = ''
    lcdx = 'Coordinates_4_LSXLSY'
    for j in range(1,5):
        if(j!=4):
            cd = cd + str(request.form.get(cdx + str(j),default=0)) + ','
        else:
            cd = cd + str(request.form.get(cdx + str(j),default=0))
    for j in range(1,3):
        if(j!=2):
            lcd = lcd + str(request.form.get(lcdx + str(j),default=0)) + ','
        else:
            lcd = lcd + str(request.form.get(lcdx + str(j),default=0))
    dis = str(request.form.get('dis',default='0'))
    a,b,c = check_coordinates(cd,st_4,coordinates_4,form_data,lcd,lsv_4,ls_4,3,dis)
    parser = ConfigParser()
    configfile = "configfile.ini"
    parser.read(configfile)
    parser.set(ja[num]['Arm'],'zone_dimensions_1',a)
    parser.set(ja[num]['Arm'] + '_SPEED', 'line_segment_coordinates_1', b)
    parser.set(ja[num]['Arm'] + '_SPEED', 'distance_1', c)
    with open('configfile.ini', 'w') as configfile:
        parser.write(configfile)
    return redirect(request.url)

@app.route('/')
def index():
    """Home page."""
    return render_template('index.html',form_data = form_data)

@app.route('/arm1')
def arm1():
    return render_template('arm1.html')

@app.route('/arm2')
def arm2():
    return render_template('arm2.html')

@app.route('/arm3')
def arm3():
    return render_template('arm3.html')

@app.route('/arm4')
def arm4():
    return render_template('arm4.html')

@app.route('/test')
def test():
    return render_template('test.html')

@app.route('/getJNdata',methods = ['POST','GET'])
def JNdata():
    return ja


if __name__ == '__main__':
    # app.run(debug=True,host='localhost',port=7000)
    app.run(debug=True,host='0.0.0.0',port=7000)