import cv2
import time
import numpy as np
import requests
from selenium import webdriver
from datetime import datetime
from PIL import Image
import time
import configparser
import urllib
from multiprocessing import Process, Queue
import boto3

s3 = boto3.client('s3')
bucket_name = 'cctvfile'
pic_sec = 0
send = 1
url = "https://alchera-face-authentication.p.rapidapi.com/v1/face/match"
headers = {
            "x-rapidapi-key": "api-key",
            "x-rapidapi-host": "alchera-face-authentication.p.rapidapi.com"
        }
    
config = configparser.ConfigParser()
config.read('/home/pi/Desktop/info.conf') #road
config = config['MAIN']

ids = config['kakaoid']
pw = config['kakaopw']


kakaoURL = 'https://accounts.kakao.com/login/kakaoforbusiness?continue=https://center-pf.kakao.com/'
ChatRoom = 'https://center-pf.kakao.com/_afxkcs/chats/4821117606519887'
options = webdriver.ChromeOptions()

#user-agent 변경
options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36")

 #크롬 드라이버 로드
driver = webdriver.Chrome('/usr/lib/chromium-browser/chromedriver', options=options)
driver.implicitly_wait(3)

#kakao main page
driver.get(kakaoURL)
time.sleep(1)

#로그인 
driver.find_element_by_id('id_email_2').send_keys(ids)
driver.find_element_by_id('id_password_3').send_keys(pw)
#driver.find_element_by_id('countryCodeRequired').find_element_by_xpath("//button[@type='3']").click()
driver.find_element_by_id('countryCodeRequired').find_element_by_xpath("//button[@tabindex='3']").click()
driver.get(ChatRoom)
time.sleep(1)

cap = cv2.VideoCapture("http://192.168.0.4:8091/?action=stream")
cascade_filename = 'haarcascade_frontalface_default.xml'
cascade = cv2.CascadeClassifier(cascade_filename)
    
def kakao():
#채팅방 로드
    #driver.get(ChatRoom)
    #time.sleep(1)
     #글 작성
    driver.find_element_by_id('chatWrite').send_keys('등록되지 않은 사람이 감지되었습니다.')  #메시지 작성           
    driver.find_element_by_xpath("//input[@class='custom uploadInput']").send_keys('/media/pi/UBUNTU 20_0/stranger/person_%d.%d.%d.%d.%d.jpg' %(now.year, now.month, now.day, now.hour, now.minute)) #사진 전송
    driver.find_element_by_xpath("//div[@class='wrap_inp']//button[@type='button']").click()

def detection(gray, frame):

    global count
    global person
    global sec
    global send
    global url
    global headers
    global pic_sec
    
    person = '/media/pi/UBUNTU 20_0/stranger/person_%d.%d.%d.%d.%d.jpg' %(now.year, now.month, now.day, now.hour, now.minute)
    
    faces = cascade.detectMultiScale(gray, scaleFactor = 1.3, minNeighbors = 5, minSize=(100, 100))
    #for (x, y, w, h) in faces:
        #cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)            
        #face_gray = gray[y:y + h, x:x + w]
        #face_color = frame[y:y + h, x:x + w]
    
    faces = np.asarray(faces)

    if faces.shape[0] > 0:
        
        if send == 1:

            cv2.imwrite(person, frame)
            pic_sec = now.second
            
            s3.upload_file(person, bucket_name, person)
            
            files = {"image": open(person, "rb")}
            response = requests.request("POST", url, headers=headers, files=files)

            string = response.text
            send = 0
            
            if "true" in string:
                print("OK")
                print("등록된 사람입니다.")
                print("\n")
                    
            else:
                kakao()
                time.sleep(0.3)
                print("stranger")
                print("등록되지 않은 사람입니다.")
                print("\n")
        
        print(sec)
        print(pic_sec)
        
        if pic_sec >= 55:
            pic_sec = 0


        if sec >= pic_sec + 5:
            send = 1
            
        else:
            send = 0

    return frame

if cap.isOpened():
    now = datetime.now()
    sec = now.second
    file_path = '/media/pi/UBUNTU 20_0/cctv/%d.%d.%d.%d.%d.avi' %(now.year, now.month, now.day, now.hour, now.minute)
    fps = 25.40
    fourcc = cv2.VideoWriter_fourcc(*'X264')
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    size = (int(width), int(height))
    out = cv2.VideoWriter(file_path, fourcc, fps, size) 
    minute = now.minute
    
    while True:

        if minute != now.minute:
            out.release()
            if minute != 0:
                filename = '/media/pi/UBUNTU 20_0/cctv/%d.%d.%d.%d.%d.avi' %(now.year, now.month, now.day, now.hour, now.minute-1)
            elif minute == 0:
                filename = '/media/pi/UBUNTU 20_0/cctv/%d.%d.%d.%d.%d.avi' %(now.year, now.month, now.day, now.hour, 59)
                
            s3.upload_file(filename, bucket_name, filename)
            file_path = file_path = '/media/pi/UBUNTU 20_0/cctv/%d.%d.%d.%d.%d.avi' %(now.year, now.month, now.day, now.hour, now.minute)
            
            out = cv2.VideoWriter(file_path, fourcc, fps, size)
            minute = now.minute
        
        now = datetime.now()
        
        ret, frame = cap.read()
            
        hour = now.hour
        sec = now.second
        
        if ret:
                
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)           
            canvas = detection(gray, frame)
            
            cv2.imshow('camera', canvas)
            out.write(frame)


            if cv2.waitKey(int(1000/fps)) != -1:
                break

        else:
            print('no frame')
            break

    
    out.release()

else:
    print("can't open camera.")

cap.release()
cv2.destroyAllWindows()
