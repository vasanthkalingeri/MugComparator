import cv2
import numpy as np
import random
import cPickle as pickle
import os
import sys
from django import template 

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

FOLDER = "data"
LIMIT = 30 #limits the number of images to be considered as part of the database
SIZE = 100

TOTAL_NO_IMAGES = 1000
NO_SIMILAR = 5
MEMORY = 'memory_file.dat'
RESULTS = 'results'

#NAME = random.sample(range(1, TOTAL_NO_IMAGES + 1), TOTAL_NO_IMAGES)
NAME = range(1, LIMIT+1)
NAME = [str(i) for i in NAME]
CASC_PATH = 'lbpcascades/lbpcascade_frontalface.xml'#'haarcascades/haarcascade_frontalface_alt.xml'
FACE_CASCADE = cv2.CascadeClassifier(CASC_PATH)

def distance(x, y, z):
    
    """Find the mean absolute error between two column vectors x and y and add z to this. Here z contains the values learnt from the user"""
    
    return sum(np.add(abs(np.subtract(x, y)), z))

    
def preprocess(image):

    """Converts the image to gray scale and also resizes the image"""
    
    global SIZE
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(image)
    
    for (x,y,w,h) in faces:
        image = image[y:y+h, x:x+w]
    
    if len(image) == 0 or image == []:
        image = None
    else:
        try:
            image = cv2.resize(image, (SIZE, SIZE))
        except:
            print image, "is the type of the image"
            image = None
    return image

def normalize_and_flatten(image):
    
    """Some normalization is applied on the image and then the image is converted into a row vector so that it can be dealt with easily"""
    
    image = image / 255.0 #For now, we apply a very naive method of normalization
    image = image.ravel()
    image -= image.mean()
    return image

def recognize_image(test_img, data, reinforce_data):
    
    """Given the test image return the index of 10 most similar hits"""
    
    global LIMIT
    #Finds the least distance between test image and the dataset
    pos = range(LIMIT - 1) # contains the indices of all the images in the database
    value = [] # will contain the mean square errors later
    for i in range(len(pos)):
        value.append(distance(test_img, data[i], reinforce_data[i]))
        if i == 0:
            continue
        k = i
        while((value[k] < value[k - 1]) and k > 0):
            #swap positions
            pos[k], pos[k - 1] = pos[k - 1], pos[k]
            #swap values
            value[k], value[k - 1] = value[k - 1], value[k]
            k -= 1
    print
    #Now pos will contain the indexes to images in ascending order of distance
    return pos, value
    
def init():

    """Load the images and the dataset randomly so as to not hamper training"""    
    
    data = np.zeros(shape=(LIMIT, SIZE*SIZE))
    images = []
    k = 0
    for itr in range(LIMIT):

        img = cv2.imread(FOLDER + "/" + NAME[itr] + ".jpg")
        img = preprocess(img)
        if img is None:
            continue
        images.append(img)
        data[k] = normalize_and_flatten(img)
        k += 1
    
    return [data, images]

def display_results(images, pos):
    
    """Displays the most similar images"""
    
            
    for i in range(NO_SIMILAR):
        cv2.imshow(str(i + 1), images[pos[i]])
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def learn(test_img, data, reinforce_data, value, mismatch_list):
    
    """Each pixel is penalized accordingly based on the error it made, this penalty is the core of the training process"""
    
    per_pix_error = value / (SIZE * SIZE)
    for i in mismatch_list:
        error = [abs(test_img[j] - data[i][j]) for j in range(len(data[i]))]
        error= [per_pix_error / (er + 0.1) for er in error]
        k = 0
        for k in range(len(reinforce_data[i])):
            reinforce_data[i][k] += error[k]
    return reinforce_data
    
def store_data(data):
    
    pickle.dump(data, open(MEMORY, 'wb'))

def print_results(data):
    
    f = open(RESULTS, 'w')
    data = [str(i) for i in data]
    s = '\n'.join(data)
    f.write(s)

def render_images(pos, test_img_path):
    
    html = """<html>
        <head><title>Similar images</title></head>

        <body>
        <h1 align="center">Test image</h1>
        <p align="center"><img src="{{ test_image }}" alt="test image"></p>

        <h1 align="center">Similar images</h1>

        <ol>
        {% for item in list %}
            <li><img src="{{ item }}" alt="similar image" height="100" width="100"></li>
            </br>
        {% endfor %}
        <ol>

        </body>
        </html>
        """    
    t = template.Template(html)
    pos = [FOLDER + "/" + str(i + 1) + ".jpg" for i in pos]
    c = template.Context({'list': pos, 'test_image': test_img_path})
    html = t.render(c)
    f = open(RESULTS + ".html", 'w')
    f.write(html)
    
def main():
    
    data, images = init()
    
    test_img_path = sys.argv[1]    
    test_img = cv2.imread(test_img_path)    
    
    #select random image to be test image
#    test_img = cv2.imread(FOLDER + "/" + str(random.randint(1, TOTAL_NO_IMAGES)) + ".jpg")
    
    test_img = preprocess(test_img)
    if test_img is None:
        print "Cannot recognize, no face found"
        return
    cv2.imshow("test", test_img)

    test_img = normalize_and_flatten(test_img)
    
    try:
        reinforce_data = pickle.load(open(MEMORY, 'rb'))
    except:    
        reinforce_data = np.zeros(shape=(LIMIT, SIZE*SIZE))
    
    i = 2
    while i >= 0:
        pos, value = recognize_image(test_img, data, reinforce_data)
        pos = pos[0:NO_SIMILAR]
        render_images(pos, test_img_path)
        s = raw_input("Enter numbers of the images which are not similar(space seperated):").split()
        mismatch_list = [pos[int(x) - 1] for x in s]
        if len(mismatch_list) == 0:
            break
        reinforce_data = learn(test_img, data, reinforce_data, max(value), mismatch_list)
        store_data(reinforce_data)
        i -= 1
        
main()

