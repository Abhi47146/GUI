import os
import urllib.request
from flask import Flask, flash, request, redirect, url_for, render_template, Response, jsonify  

from werkzeug.utils import secure_filename
import cv2
import numpy as np
from configparser import ConfigParser
import socket
import json 

app = Flask(__name__)

hostname = socket.gethostname()
ipadd = socket.gethostbyname(hostname)

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
c=0
for arm in arms:
    st = parser.get(arm,'STREAM')
    stream.append(st)
    ja.append(
            {
                'Junction_scn':junction_scn,
                'Arm':arm,
                'Zone':'0,0,0,0,0,0,0,0',
                'Line_segment':'0,0,0,0',
                'Distance':'0',
                'Port':parser.get('DEFAULT','LPU_PORT'),
                'Stream':st,
                'Status':'ON',
                'IPadd':'',
                'Edit': '1',
            }
        )
    armsp = arm + '_SPEED'
    try:
        parser.add_section(armsp)
        print(armsp)
        # parser.set(armsp, 'line_segment_coordinates_1', '')
        parser.set(armsp, 'distance_1', '')
        parser.set(armsp, 'status', '')
    except:
        # parser.set(armsp, 'line_segment_coordinates_1', '')
        parser.set(armsp, 'distance_1', '')
        parser.set(armsp, 'status', '')
    try:
        camera = cv2.VideoCapture(ja[c]["Stream"])
        success, frame = camera.read()
        if success:
            parser.set(ja[c]['Arm'] + '_SPEED', 'status', 'ON')
            ja[c]['Status'] = 'ON'
    except:
        parser.set(ja[c]['Arm'] + '_SPEED', 'status', 'OFF')
        ja[c]['Status'] = 'OFF'
    c += 1
with open('configfile.ini', 'w') as configfile:
    parser.write(configfile)
#camera = cv2.VideoCapture('/home/itspe/Videos/J091_L01/WhatsApp Video 2022-12-15 at 10.57.22 AM.mp4')  # use 0 for web camera
#  for cctv camera use rtsp://username:password@ip_address:554/user=username_password='password'_channel=channel_number_stream=0.sdp' instead of camera
# for local webcam use cv2.VideoCapture(0)
coordinates_1 = '0,0,0,0,0,0,0,0'
coordinates_2 = '0,0,0,0,0,0,0,0'
coordinates_3 = '0,0,0,0,0,0,0,0'
coordinates_4 = '0,0,0,0,0,0,0,0'
coordinates_5 = '0,0,0,0,0,0,0,0'
lsv_1 = '0,0,0,0'
lsv_2 = '0,0,0,0'
lsv_3 = '0,0,0,0'
lsv_4 = '0,0,0,0'
lsv_5 = '0,0,0,0'
st_1 = junction_scn + ' Arm_1 Zone Coordinates'
st_2 = junction_scn + ' Arm_2 Zone Coordinates'
st_3 = junction_scn + ' Arm_3 Zone Coordinates'
st_4 = junction_scn + ' Arm_4 Zone Coordinates'
st_5 = junction_scn + ' Arm_5 Zone Coordinates'
ls_1 = junction_scn + ' Arm_1 Line Segment'
ls_2 = junction_scn + ' Arm_2 Line Segment'
ls_3 = junction_scn + ' Arm_3 Line Segment'
ls_4 = junction_scn + ' Arm_4 Line Segment'
ls_5 = junction_scn + ' Arm_5 Line Segment'

form_data = {
    st_1:'',
    ls_1:'',
    st_2:'',
    ls_2:'',
    st_3:'',
    ls_3:'',
    st_4:'',
    ls_4:'',
    st_5:'',
    ls_5:'',
}
"""
Below Functions are for reading and writing in our config file
"""
def config_read():
    parser = ConfigParser()
    configfile = "configfile.ini"
    parser.read(configfile)
    return parser

def config_write(parser):
    with open('configfile.ini', 'w') as configfile:
        parser.write(configfile)

"""
Below functions are used when only the camera scn is changed
"""

def change_idlist(lis,cscn,pscn):
    ans = ''
    for i in range(len(lis)):
        if(i!=0):
            if(lis[i]==pscn):
                ans = ans + "," + cscn
            else:
                ans = ans + "," + lis[i]
        else:
            if(lis[i]==pscn):
                ans = ans + cscn
            else:
                ans = ans + lis[i]
    return ans

def change_amrid(cscn,pscn,parser):
    list_arm = parser.get('DEFAULT','ARM_IDS')
    lis = list(list_arm.split(","))
    arm_ids = change_idlist(lis,cscn,pscn)
    change_armid_fields(cscn,pscn,parser)
    parser.set('DEFAULT','arm_ids',arm_ids)


"""
Below functions are used when the junction scn is changed
"""
def change_allidlist(scn,cscn,pscn,parser):
    list_arm = parser.get('DEFAULT','ARM_IDS')
    lis = list(list_arm.split(","))
    dic,ans = {},''
    for j in range(len(lis)):
        if(j==0):
            if(lis[j]==pscn):
                ans = cscn
                dic[lis[j]] = cscn
            else:
                tem = lis[j].split("_")
                temp = scn + "_" + tem[1]
                ans = temp
                dic[lis[j]] = temp
        else:
            if(lis[j]==pscn):
                ans = ans + "," + cscn
                dic[lis[j]] = cscn
            else:
                tem = lis[j].split("_")
                temp = scn + "_" + tem[1]
                ans = ans + "," + temp
                dic[lis[j]] = temp
    return dic,ans


def change_all(scn,cscn,pscn,parser):
    dic,arm_ids = change_allidlist(scn,cscn,pscn,parser)
    c = 0
    print(dic)
    for key in dic.keys():
        change_armid_fields(dic[key],key,parser)
        ja[c]['Arm'] = dic[key]
        c += 1
    parser.set('DEFAULT','junction_scn',scn)
    parser.set('DEFAULT','arm_ids',arm_ids)


"""
Below function is used to check if there are any changes in junction_scn or camera_scn
"""
def check_scn(cscn,pscn,parser,num):
    temp = list(cscn.split("_"))
    scn = temp[0]
    if scn==parser.get('DEFAULT','JUNCTION_SCN'):
        print("Why this")
        if(cscn!=pscn):
            change_amrid(cscn,pscn,parser)
            ja[num]['Arm'] = cscn
    else:
        if(cscn!=pscn):
            print(scn,cscn,"Only THis")
            change_all(scn,cscn,pscn,parser)

"""
Below functions are used for making changes in our config file
"""

def addcamera(scn,stream,port):
    parser = config_read()
    arm_ids = parser.get('DEFAULT','ARM_IDS')
    if("," in arm_ids):
        arm_ids = arm_ids + "," + scn
    parser = add_section(parser,scn,stream)
    parser.set('DEFAULT','arm_ids',arm_ids)
    if(parser.get('DEFAULT','LPU_PORT')!=port):
        parser.set('DEFAULT', 'lpu_port', port)
        for element in ja:
            element['Port'] = port
    config_write(parser)

def add_section(parser,scn,stream):
    parser.add_section(scn)
    parser.set(scn, 'stream', stream)
    parser.set(scn, 'number_of_zones', '1')
    parser.set(scn, 'zone_dimensions_1', '')

    armsp = scn + "_SPEED"
    parser.add_section(armsp)
    parser.set(armsp, 'line_segment_coordinates_1', '')
    parser.set(armsp, 'distance_1', '')
    parser.set(armsp, 'status', '')
    ja.append(
            {
                'Junction_scn':parser.get('DEFAULT','JUNCTION_SCN'),
                'Arm':scn,
                'Zone':'0,0,0,0,0,0,0,0',
                'Line_segment':'0,0,0,0',
                'Distance':'0',
                'Port':parser.get('DEFAULT','LPU_PORT'),
                'Stream':stream,
                'Status':'ON',
                'IPadd':'',
                'Edit': '1',
            }
        )
    
    num = len(ja) -1
    if stream!='':
        try:
            camera = cv2.VideoCapture(stream)
            success, frame = camera.read()
            if success:
                print(ja[num]['Arm'])
                parser.set(ja[num]['Arm'],'stream',stream)
                ja[num]['Stream'] = stream
                parser.set(ja[num]['Arm'] + '_SPEED', 'status', 'ON')
                ja[num]['Status'] = 'ON'
        except:
            parser.set(ja[num]['Arm'] + '_SPEED', 'status', 'OFF')
            ja[num]['Status'] = 'OFF'
    return parser


def deleterow(row):
    parser = config_read()
    arm_ids = parser.get('DEFAULT','ARM_IDS')
    delarm = ja[row]['Arm']
    print(delarm)
    try:
        parser.remove_section(delarm)
        parser.remove_section(delarm + '_SPEED')
    except:
        pass
    lis = arm_ids.split(",")
    c = 0
    ans = ''
    for arm in lis:
        if(c==0):
            if(arm==delarm):
                ans = ''
            else:
                ans = arm
        else:
            if(arm==delarm):
                ans = ans
            else:
                ans = ans + "," + arm
        c += 1
    parser.set('DEFAULT','arm_ids',ans)
    ja.pop(row)
    print(ja)
    config_write(parser)

def change_armid_fields(cscn,pscn,parser):
    try:
        print(cscn,pscn)
        parser.add_section(cscn)
        parser.set(cscn, 'stream', parser.get(pscn,'STREAM'))
        parser.set(cscn, 'number_of_zones', parser.get(pscn,'NUMBER_OF_ZONES'))
        parser.set(cscn, 'zone_dimensions_1', parser.get(pscn,'ZONE_DIMENSIONS_1'))
    except:
        parser.set(cscn, 'stream', parser.get(pscn,'STREAM'))
        parser.set(cscn, 'number_of_zones', parser.get(pscn,'NUMBER_OF_ZONES'))
        parser.set(cscn, 'zone_dimensions_1', parser.get(pscn,'ZONE_DIMENSIONS_1'))
    armsp = cscn + '_SPEED'
    parmsp = pscn + '_SPEED'
    try:
        parser.add_section(armsp)
        parser.set(armsp, 'line_segment_coordinates_1', parser.get(parmsp,'line_segment_coordinates_1'))
        parser.set(armsp, 'distance_1', parser.get(parmsp,'distance_1'))
        parser.set(armsp, 'status', parser.get(parmsp,'status'))
    except:
        parser.set(armsp, 'line_segment_coordinates_1', parser.get(parmsp,'line_segment_coordinates_1'))
        parser.set(armsp, 'distance_1', parser.get(parmsp,'distance_1'))
        parser.set(armsp, 'status', parser.get(parmsp,'status'))
    parser.remove_section(pscn)
    parser.remove_section(parmsp)

def changeconfig(scn,stream,num,port):
    parser = config_read()
    pscnl = parser.get('DEFAULT','ARM_IDS')
    pscn = list(pscnl.split(","))[num]
    if len(scn)>=8 and len(scn)<=9:
        check_scn(scn,pscn,parser,num) # Will change SCN here
    if stream!='':
        try:
            camera = cv2.VideoCapture(stream)
            success, frame = camera.read()
            if success:
                print(ja[num]['Arm'])
                parser.set(ja[num]['Arm'],'stream',stream)
                ja[num]['Stream'] = stream
                parser.set(ja[num]['Arm'] + '_SPEED', 'status', 'ON')
                ja[num]['Status'] = 'ON'
        except:
            parser.set(ja[num]['Arm'] + '_SPEED', 'status', 'OFF')
            ja[num]['Status'] = 'OFF'
    if(parser.get('DEFAULT','LPU_PORT')!=port):
        parser.set('DEFAULT', 'lpu_port', port)
        for element in ja:
            element['Port'] = port
    config_write(parser)

def store_data(num,a,b,c):
    parser = config_read()
    parser.set(ja[num]['Arm'],'zone_dimensions_1',a)
    parser.set(ja[num]['Arm'] + '_SPEED', 'line_segment_coordinates_1', b)
    parser.set(ja[num]['Arm'] + '_SPEED', 'distance_1', c)
    config_write(parser)

"""
Below functions are used for making checking if the data is correct for storing or not
"""

def get_coordinates(cdx,lcdx):
    cd,lcd = '',''
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
    return cd,lcd,dis

def check_coordinates(cd,st,coordinates,form_data,lcd,lsv,lst,num,dis):
    if(cd!=',,,'):
        try:
            t = len(list(map(int,cd.split(","))))
            if(t==8):
                coordinates = cd
                form_data[st] = coordinates
                ja[num]['Zone'] = coordinates
        except:
            coordinates = coordinates
    if(lcd!=','):
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

"""
Below function is used for generating frames for our video
"""
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

"""
Below functions are used for routing to our API endpoints
"""

@app.route('/arm1/video_feed')
def video_feed_1():
    #Video streaming route. Put this in the src attribute of an img tag
    if(armslen>=1):
        camera = cv2.VideoCapture(ja[0]['Stream'])
        coordinates_1 = ja[0]['Zone']
        lsv_1 = ja[0]['Line_segment']
        return Response(gen_frames(camera,coordinates_1,lsv_1), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(request.url)

@app.route('/arm2/video_feed')
def video_feed_2():
    #Video streaming route. Put this in the src attribute of an img tag
    if(armslen>=2):
        camera = cv2.VideoCapture(ja[1]['Stream'])
        coordinates_2 = ja[1]['Zone']
        lsv_2 = ja[1]['Line_segment']
        return Response(gen_frames(camera,coordinates_2,lsv_2), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(request.url)

@app.route('/arm3/video_feed')
def video_feed_3():
    #Video streaming route. Put this in the src attribute of an img tag
    if(armslen>=3):
        camera = cv2.VideoCapture(ja[2]['Stream'])
        coordinates_3 = ja[2]['Zone']
        lsv_3 = ja[2]['Line_segment']
        return Response(gen_frames(camera,coordinates_3,lsv_3), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(request.url)

@app.route('/arm4/video_feed')
def video_feed_4():
    #Video streaming route. Put this in the src attribute of an img tag
    if(armslen>=4):
        camera = cv2.VideoCapture(ja[3]['Stream'])
        coordinates_4 = ja[3]['Zone']
        lsv_4 = ja[3]['Line_segment']
        return Response(gen_frames(camera,coordinates_4,lsv_4), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(request.url)

@app.route('/arm5/video_feed')
def video_feed_5():
    #Video streaming route. Put this in the src attribute of an img tag
    if(armslen>=5):
        camera = cv2.VideoCapture(ja[4]['Stream'])
        coordinates_5 = ja[4]['Zone']
        lsv_5 = ja[4]['Line_segment']
        return Response(gen_frames(camera,coordinates_5,lsv_5), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(request.url)


@app.route('/')
def index():
    """Home page."""
    return render_template('index.html')

 #below function is to fetch the dimensions that arr stored in config  

@app.route('/arm<int:arm_number>')
def arm(arm_number):
    # Get the dimensions and line dimensions based on the arm_number
    if arm_number == 1:
        dimensions = parser.get('J091_L01', 'zone_dimensions_1')
        line_dimensions = parser.get('J091_L01_SPEED', 'line_segment_coordinates_1')
    elif arm_number == 2:
        dimensions = parser.get('J091_L02', 'zone_dimensions_1')
        line_dimensions = parser.get('J091_L02_SPEED', 'line_segment_coordinates_1')
    elif arm_number == 3:
        dimensions = parser.get('J091_L03', 'zone_dimensions_1')
        line_dimensions = parser.get('J091_L03_SPEED', 'line_segment_coordinates_1')
    elif arm_number == 4:
        dimensions = parser.get('J091_L04', 'zone_dimensions_1')
        line_dimensions = parser.get('J091_L04_SPEED', 'line_segment_coordinates_1')
    else:
        # Handle invalid arm_number
        return "Invalid arm_number", 400

    return render_template('arm{}.html'.format(arm_number), dimensions=json.dumps(dimensions), line_dimensions=json.dumps(line_dimensions))






 #below function is to set the dimensions that are stored in config  

@app.route('/update_config', methods=['POST'])
def update_config():

    # Get the new value from the request
    data = request.json

    # Extract data from the request
    dimensions = data['dimension']
    line_dimensions = data['line_dimensions']
    camNumber = data['camNumber']

    parser = config_read()

    # Set configurations based on camNumber
    if camNumber == '1':
        parser.set('J091_L01', 'zone_dimensions_1', dimensions)
        parser.set('J091_L01_SPEED', 'line_segment_coordinates_1', line_dimensions)
    elif camNumber == '2':
        parser.set('J091_L02', 'zone_dimensions_1', dimensions)
        parser.set('J091_L02_SPEED', 'line_segment_coordinates_1', line_dimensions)
    elif camNumber == '3':
        parser.set('J091_L03', 'zone_dimensions_1', dimensions)
        parser.set('J091_L03_SPEED', 'line_segment_coordinates_1', line_dimensions)
    elif camNumber == '4':
        parser.set('J091_L04', 'zone_dimensions_1', dimensions)
        parser.set('J091_L04_SPEED', 'line_segment_coordinates_1', line_dimensions)
    else:
        # Handle invalid camNumber
        return "Invalid camNumber: " + camNumber, 400

    # Write updated configurations to the file
    config_write(parser)

    response = {
        'dimensions': dimensions,
        'line_dimensions': line_dimensions
    }

    return jsonify(response), 200



@app.route('/test')
def test():
    return render_template('home.html')

@app.route('/',methods = ['POST'])
def test1():
    if request.method == 'POST':
        if request.form.get('add_cam') is None:
            scn = request.form.get('scn')
            stream = request.form.get('stream')
            num = int(request.form.get('row')) - 1
            port = request.form.get('port')
            changeconfig(scn,stream,num,port)
        else:
            scn = request.form.get('scn')
            stream = request.form.get('stream')
            port = request.form.get('port')
            addcamera(scn,stream,port)
        return render_template('index.html')
    else:
        return render_template('index.html')



@app.route('/getJNdata',methods = ['POST','GET'])
def JNdata():
    return ja

@app.route('/delete',methods = ['POST'])
def delete():
    if request.method == "POST":
        jsonData = request.get_json()
        deleterow(jsonData['row'])
    return render_template('index.html')

if __name__ == '__main__':
    # app.run(debug=True,host='localhost',port=80)
    app.run(debug=True,host='0.0.0.0',port=88)