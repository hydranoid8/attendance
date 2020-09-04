from tkinter import *
from tkinter import ttk
import RPi.GPIO as GPIO
import sys
import os
import numpy as np
from face_recognition_system.videocamera import VideoCamera
from face_recognition_system.detectors import FaceDetector
import face_recognition_system.operations as op
import cv2
from cv2 import __version__
import time
import hashlib
from pyfingerprint.pyfingerprint import PyFingerprint
import csv
from datetime import datetime
import requests
from gpiozero import Buzzer
from time import sleep

global doorVar
doorVar = 0
buzzer = Buzzer(17)
buzzer.on()

#global fingerprint_retries
#fingerprint_retries = []

def buzzer_success():
    buzzer.off()
    sleep(.1)
    buzzer.on()
    sleep(.1)
    buzzer.off()
    sleep(.1)
    buzzer.on()
    sleep(.1)
    buzzer.off()
    sleep(.1)
    buzzer.on()
    sleep(.1)
    
def buzzer_alert():
    buzzer.off()
    sleep(3)
    buzzer.on()

def sendmail_callback(channel):
    print("Sending e-mail......")
    res = requests.post(
        "https://api.mailgun.net/v3/sandbox43e072b20eb24ec0b3cc16e021d54ee6.mailgun.org/messages",
        auth=("api", "f60077eec008089c135d40c01b5cda92-e470a504-888b5d0c"),
        files=[("attachment", ("neighbour.jpg", open("2.jpg", "rb").read()))],
        data={"from": "A Person from Door <mailgun@sandbox43e072b20eb24ec0b3cc16e021d54ee6.mailgun.org>",
            "to": ["kamrul.hassan@northsouth.edu"],
            "subject": "Hello from Your Door!",
            "text": "I was here!!!"})
    print(res.text)
    print(res.status_code)
    print("mail was sent")
    time.sleep(10)

def malacious_sendmail():
    print("Sending intruder e-mail......")
    res = requests.post(
        "https://api.mailgun.net/v3/sandbox43e072b20eb24ec0b3cc16e021d54ee6.mailgun.org/messages",
        auth=("api", "f60077eec008089c135d40c01b5cda92-e470a504-888b5d0c"),
        files=[("attachment", ("intruder.jpg", open("2.jpg", "rb").read()))],
        data={"from": "An Intruder Alert from Door <mailgun@sandbox43e072b20eb24ec0b3cc16e021d54ee6.mailgun.org>",
            "to": ["kamrul.hassan@northsouth.edu"],
            "subject": "Alert!!! Intruder from Your Door!",
            "text": "Intruder was here!!!"})
    print(res.text)
    print(res.status_code)
    print("mail was sent")
    time.sleep(10)
    
    
def recognize_finger():
    try:
        f = PyFingerprint('/dev/ttyUSB0', 57600, 0xFFFFFFFF, 0x00000000)

        if ( f.verifyPassword() == False ):
            raise ValueError('The given fingerprint sensor password is wrong!')

    except Exception as e:
        print('The fingerprint sensor could not be initialized!')
        print('Exception message: ' + str(e))
        exit(1)

    ## Gets some sensor information
    print('Currently used templates: ' + str(f.getTemplateCount()) +'/'+ str(f.getStorageCapacity()))

    ## Tries to search the finger and calculate hash
    try:
        print('Waiting for finger...')

        ## Wait that finger is read
        while ( f.readImage() == False ):
            pass

        ## Converts read image to characteristics and stores it in charbuffer 1
        f.convertImage(0x01)

        ## Searchs template
        result = f.searchTemplate()

        positionNumber = result[0]
        #accuracyScore = result[1]

        if ( positionNumber == -1 ):
            print('No match found!')
            return -2
        else:
            print('Found template at position #' + str(positionNumber))
            #print('The accuracy score is: ' + str(accuracyScore))

        ## OPTIONAL stuff

        ## Loads the found template to charbuffer 1
        f.loadTemplate(positionNumber, 0x01)

        ## Downloads the characteristics of template loaded in charbuffer 1
        characterics = str(f.downloadCharacteristics(0x01)).encode('utf-8')

        ## Hashes characteristics of template
        print('SHA-2 hash of template: ' + hashlib.sha256(characterics).hexdigest())
        return positionNumber

    except Exception as e:
        print('Operation failed!')
        print('Exception message: ' + str(e))
        exit(1)

def enroll_finger():
    try:
        f = PyFingerprint('/dev/ttyUSB0', 57600, 0xFFFFFFFF, 0x00000000)

        if ( f.verifyPassword() == False ):
            raise ValueError('The given fingerprint sensor password is wrong!')

    except Exception as e:
        print('The fingerprint sensor could not be initialized!')
        print('Exception message: ' + str(e))
        exit(1)

    ## Gets some sensor information
    print('Currently used templates: ' + str(f.getTemplateCount()) +'/'+ str(f.getStorageCapacity()))

    ## Tries to enroll new finger
    try:
        import hashlib
        print('Waiting for finger...')

        ## Wait that finger is read
        while ( f.readImage() == False ):
            pass

        ## Converts read image to characteristics and stores it in charbuffer 1
        f.convertImage(0x01)

        ## Checks if finger is already enrolled
        result = f.searchTemplate()
        positionNumber = result[0]

        if ( positionNumber >= 0 ):
            print('Template already exists at position #' + str(positionNumber))
            exit(0)

        print('Remove finger...')
        time.sleep(2)

        print('Waiting for same finger again...')

        ## Wait that finger is read again
        while ( f.readImage() == False ):
            pass

        ## Converts read image to characteristics and stores it in charbuffer 2
        f.convertImage(0x02)

        ## Compares the charbuffers
        if ( f.compareCharacteristics() == 0 ):
            raise Exception('Fingers do not match')

        ## Creates a template
        f.createTemplate()

        ## Saves template at new position number
        positionNumber = f.storeTemplate()
        print('Finger enrolled successfully!')
        print('New template position #' + str(positionNumber))

    except Exception as e:
        print('Operation failed!')
        print('Exception message: ' + str(e))
        exit(1)


def get_images(frame, faces_coord, shape):
    """ Perfrom transformation on original and face images.

    This function draws the countour around the found face given by faces_coord
    and also cuts the face from the original image. Returns both images.
    """
    if shape == "rectangle":
        faces_img = op.cut_face_rectangle(frame, faces_coord)
        frame = op.draw_face_rectangle(frame, faces_coord)
    faces_img = op.normalize_intensity(faces_img)
    faces_img = op.resize(faces_img)
    return (frame, faces_img)

def add_person(people_folder, shape, user_name):
    """ Funtion to add pictures of a person
    """
    folder = people_folder + str(user_name)
    if not os.path.exists(folder):
        os.mkdir(folder)
        video = VideoCamera()
        detector = FaceDetector('face_recognition_system/frontal_face.xml')
        counter = 1
        timer = 0
        cv2.namedWindow('Video Feed', cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow('Saved Face', cv2.WINDOW_NORMAL)
        while counter < 5:
            # I changed it to 11 to get 10 pics, it was 5
            frame = video.get_frame()
            frame = cv2.flip(frame, -1)
            face_coord = detector.detect(frame)
            if len(face_coord):
                frame, face_img = get_images(frame, face_coord, shape)
                # save a face every second, we start from an offset '5' because
                # the first frame of the camera gets very high intensity
                # readings.
                if timer % 100 == 5:
                    cv2.imwrite(folder + '/' + str(counter) + '.jpg',
                                face_img[0])
                    print ('Images Saved:' + str(counter))
                    counter += 1
                    cv2.imshow('Saved Face', face_img[0])
                    if counter == 5:
                        # I changed it to 11 to get 10 pics, it was 5
                        cv2.waitKey(1)
                        cv2.destroyAllWindows()
                        for i in range(0,5):
                            cv2.waitKey(1)
                        break

            cv2.imshow('Video Feed', frame)
            cv2.waitKey(50)
            timer += 5
    else:
        print ("This name already exists.")
        sys.exit()

def recognize_people(people_folder, shape, detection_mode):
    """ Start recognizing people in a live stream with your webcam
    """
    fingerprint_retries = []
    counter = 1
    try:
        people = [person for person in os.listdir(people_folder)]
    except:
        print ("Have you added at least one person to the system?")
        sys.exit()
    print ("This are the people in the Recognition System:")
    for person in people:
        print ("-" + person)

    print (30 * '-')
    
    detector = FaceDetector('face_recognition_system/frontal_face.xml')
    
    recognizer = cv2.face.EigenFaceRecognizer_create()
    threshold = 4000
    images = []
    labels = []
    labels_people = {}
    for i, person in enumerate(people):
        labels_people[i] = person
        for image in os.listdir(people_folder + person):
            images.append(cv2.imread(people_folder + person + '/' + image, 0))
            labels.append(i)
    try:
        recognizer.train(images, np.array(labels))
    except:
        print ("\nOpenCV Error: Do you have at least two people in the database?\n")
        sys.exit()

    video = VideoCamera()
    while True:
        frame = video.get_frame()
        frame = cv2.flip(frame, -1)
        cv2.imwrite("2.jpg", frame)
        faces_coord = detector.detect(frame, False)
        if len(faces_coord):
            frame, faces_img = get_images(frame, faces_coord, shape)
            for i, face_img in enumerate(faces_img):
                if __version__ == "3.1.0":
                    collector = cv2.face.MinDistancePredictCollector()
                    recognizer.predict(face_img, collector)
                    conf = collector.getDist()
                    pred = collector.getLabel()
                else:
                    pred, conf = recognizer.predict(face_img)
                print ("Prediction: " + str(pred))
                #print ('Confidence: ' + str(round(conf)))
                #print ('Threshold: ' + str(threshold))
                if conf < threshold:
                    cv2.putText(frame, labels_people[pred].capitalize(),
                                (faces_coord[i][0], faces_coord[i][1] - 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1,
                                cv2.LINE_AA)
                    if detection_mode == 'door_lock':
                        print('Accessing as ' + labels_people[pred] + '......')
                        print('Please verify yourself with fingerprint...')
                        fingerprint_label = recognize_finger()
                        if(int(fingerprint_label) == int(pred)):
                            #print (int(pred))
                            print('Access granted...')
                            print('Unlocking door....')
                            GPIO.output(14, True)
                            GPIO.output(24, False)
                            buzzer_success()
                            time.sleep(5)
                            GPIO.output(24, True)
                            GPIO.output(14, False)
                            print('Door Unlocked!')
                            now = datetime.now()
                            now_string = now.strftime("%d/%m/%Y %H:%M:%S")
                            with open('door_unlock_data.csv', mode='a') as door_data:
                                door_writer = csv.writer(door_data, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                                door_writer.writerow([str(counter), str(pred),str(labels_people[pred]), str(now_string)])
                            counter += 1
                        else:
                            #print (int(pred))
                            fingerprint_retries.append(labels_people[pred])
                            print(fingerprint_retries)
                            if len(fingerprint_retries) == 3:
                                if len(set(fingerprint_retries)) == 1:
                                    malacious_sendmail()
                                fingerprint_retries = []
                            print('Fingerprint isn\'t matched')
                            print('Access Denied!!!')
                            buzzer_alert()
                        if pred != -1:
                            cv2.waitKey(1)
                            cv2.destroyAllWindows()
                            for i in range(0,5):
                                cv2.waitKey(1)
                        for i in range(0,100):
                            frame = video.get_frame()
                            frame = cv2.flip(frame, -1)
                        continue
                    
                    elif detection_mode == 'attendance':
                        name_attended = labels_people[pred]
                        is_attended = 0
                        print('Detected '+ name_attended)
                        now = datetime.now()
                        now_string = now.strftime("%d/%m/%Y %H:%M:%S")
                        with open('attendance_data.csv', mode='r') as attendance_data:
                            attendances = csv.reader(attendance_data)
                            for row in attendances:
                                if row[2] == name_attended:
                                    is_attended = 1
                        if is_attended == 1:
                            print(name_attended + ' is already attended')
                        elif is_attended == 0:
                            with open('attendance_data.csv', mode='a') as attendance_data:
                                attendance_writer = csv.writer(attendance_data, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                                attendance_writer.writerow([str(counter), str(pred),str(labels_people[pred]), str(now_string)])
                        counter += 1
                        
                else:
                    cv2.putText(frame, "Unknown",
                                (faces_coord[i][0], faces_coord[i][1]),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1,
                                cv2.LINE_AA)

        cv2.putText(frame, "ESC to exit", (5, frame.shape[0] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255, 255), 1, cv2.LINE_AA)
        cv2.imshow('Live Video Transmission', frame)
        if cv2.waitKey(100) & 0xFF == 27:
            sys.exit()

def check_choice():
    """ Check if choice is good
    """
    is_valid = 0
    while not is_valid:
        try:
            choice = int(input('Enter 1 to exit : '))
            if choice in [1, 2, 3]:
                is_valid = 1
            else:
                print ("'%d' is not an option.\n" % choice)
        except ValueError:
            print ("%s is not an option.\n" % str(error).split(": ")[1])
    return choice

def enroll_person(*args):
    PEOPLE_FOLDER = "face_recognition_system/people/"
    SHAPE = "rectangle"
    if not os.path.exists(PEOPLE_FOLDER):
        os.makedirs(PEOPLE_FOLDER)
    add_person(PEOPLE_FOLDER, SHAPE, user_name.get())

def get_attendance(*args):
    PEOPLE_FOLDER = "face_recognition_system/people/"
    SHAPE = "rectangle"
    os.system("sudo modprobe bcm2835-v4l2")
    detection_mode = 'attendance'
    recognize_people(PEOPLE_FOLDER, SHAPE, detection_mode)

def recognize_door_people(*args):
    PEOPLE_FOLDER = "face_recognition_system/people/"
    SHAPE = "rectangle"
    os.system("sudo modprobe bcm2835-v4l2")
    detection_mode = 'door_lock'
    recognize_people(PEOPLE_FOLDER, SHAPE, detection_mode)
    
def set_username(*args):
    username = user_name.get()
    print(username)
    user_name.set(username)
    enroll_finger()
    print('Enrolling face...')
    enroll_person()
    print('Enrolling Finished....')
    sys.exit()

def door_lock(*args):
    door = Toplevel(root, padx=50, pady=50)
    door.title('Door Lock Management')
    door.geometry('400x300')
    door.rowconfigure(2,minsize=20)
    namelabel = ttk.Label(door, text='Enter Username: ',font='Helvetica 14 bold')
    namelabel.grid(column=0,row=1)
    nameentry = ttk.Entry(door, width=20, textvariable=user_name)
    nameentry.grid(column=1, row=1, sticky=(W, E))
    nameentry.focus()
    door.rowconfigure(4, minsize=20)
    text_show = StringVar()
    fingerprintalert = ttk.Label(door, textvariable=finger_alert).grid(column=1, row=5, sticky=W)
    show_text_alert = ttk.Label(door, textvariable=text_show).grid(column=1, row=6, sticky=W)
    nameinput = ttk.Button(door, text="OK", command=set_username).grid(column=1,row=3, sticky=W)
    if(doorVar == 1):
        door.destroy()



def attendance_management(*args):
    attendance = Toplevel(root, padx=50, pady=50)
    attendance.title('Attendance Management')
    attendance.geometry('400x300')
    attendance.rowconfigure(2,minsize=20)
    namelabel = ttk.Label(attendance, text='Enter Username: ',font='Helvetica 14 bold')
    namelabel.grid(column=0,row=1)
    nameentry = ttk.Entry(attendance, width=20, textvariable=user_name)
    nameentry.grid(column=1, row=1, sticky=(W, E))
    nameentry.focus()
    nameinput = ttk.Button(attendance, text="OK", command=set_username).grid(column=1,row=3, sticky=W)
    attendance.rowconfigure(4, minsize=20)
    fingerprintalert = ttk.Label(attendance, textvariable=finger_alert).grid(column=1, row=5, sticky=W)

if __name__ == '__main__':
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(14, GPIO.OUT)
    GPIO.setup(24, GPIO.OUT)

    GPIO.add_event_detect(23,GPIO.RISING,callback=sendmail_callback)
    root = Tk()
    root.title("2FA Attendance")

    mainframe = ttk.Frame(root, padding="100 50 100 100")
    mainframe.grid(column=0, row=0, sticky=(N, W, E, S))

    user_name = StringVar()
    finger_alert = StringVar()
    text_show = StringVar()

    ttk.Label(mainframe, text="Door Lock Management", font='Helvetica 18 bold').grid(column=1, row=1, sticky=(W,E))
    ttk.Button(mainframe, text="Enroll User", command=door_lock).grid(column=1, row=2, sticky=(W,E))
    ttk.Button(mainframe, text="Check", command=recognize_door_people).grid(column=1, row=3, sticky=(W,E))
    ttk.Label(mainframe).grid(column=2, row=2, sticky=(W,E))

    ttk.Label(mainframe, text="Attendance Management", font='Helvetica 18 bold').grid(column=3, row=1, sticky=(W,E))
    ttk.Button(mainframe, text="Enroll User", command=attendance_management).grid(column=3, row=2, sticky=(W,E))
    ttk.Button(mainframe, text="Attendance Monitor", command=get_attendance).grid(column=3, row=3, sticky=(W,E))

    for child in mainframe.winfo_children(): child.grid_configure(padx=5, pady=5)
    root.mainloop()

    print (30 * '-')
    print (" ACTIONS")
    print (30 * '-')
    print ("1. Exit")
    print (30 * '-')

    CHOICE = check_choice()

    PEOPLE_FOLDER = "face_recognition_system/people/"
    SHAPE = "rectangle"

    if CHOICE == 1:
        sys.exit()
        