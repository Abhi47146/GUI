import cv2

def nayanam_rtsp(path, dim_list, frame_count):
    cap = cv2.VideoCapture(path)

    LINE_X1,LINE_Y1,LINE_X2,LINE_Y2 = dim_list
    
    frame = 0

    while(cap.isOpened()):
        try:
            _,image_data = cap.read()
            image_dat = cv2.resize(image_data,(640,640))
        except:
            break       
        frame = frame + 1

        if frame == frame_count:
            cv2.imwrite("image.png",image_dat)
            break
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break
    

path = '/home/itspe/Videos/J091_L01/pexels-kelly-lacy-5473765.mp4'
dim_list = [235,405,700,560]
frame_count = 30
nayanam_rtsp(path, dim_list, frame_count)
