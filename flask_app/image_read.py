import cv2
import numpy as np
path = "image.png"    

font = cv2.FONT_HERSHEY_SIMPLEX
# fontScale
fontScale = 1

fontScale_l = 1
# Blue color in BGR
color = (255, 255, 255)
color1 = (255,0,0)
# Line thickness of 2 px
thickness = 2
thickness_l = 3
# Using cv2.putText() method


frame = cv2.imread(path)
frame = cv2.resize(frame,(640,640))
start_point = (198,324)
end_point = (407,324)
frame = cv2.line(frame, start_point, end_point, color1, thickness_l)
frame = cv2.putText(frame, 'LSX1,' + "LSY1", start_point, font,fontScale_l, color, thickness, cv2.LINE_AA)
frame = cv2.putText(frame, 'LSX2,' + "LSY2", end_point, font,fontScale_l, color, thickness, cv2.LINE_AA)


dim_list = [[134,536],[508,536],[448,421], [164,421]]
j = 1
for cord in dim_list:
    image = cv2.putText(frame, 'X' + str(j) + ",Y" + str(j), cord, font,fontScale, color, thickness, cv2.LINE_AA)
    j += 1
pts = np.array(dim_list,
               np.int32)
frame = cv2.polylines(frame, [pts] ,True, (255,0,0), 2)
cv2.imwrite(path,frame)
while(1):
    cv2.imshow('image', frame)
    if cv2.waitKey(20) & 0xFF == 27:
        break
         
cv2.destroyAllWindows()