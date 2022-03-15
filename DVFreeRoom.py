import requests,inquirer,re         #inquirer, alternative of whaaaaat prompt
from pprint import pprint          #for debug
from whaaaaat import prompt         #for CLI
from datetime import datetime       #to get datetime
from pwinput import pwinput         #password replacement with asterisks
from bs4 import BeautifulSoup       #web scrapping

#### Disclaimer :

#PYTHON VERSION !!! > 3.9 and < 3.10(use python --version)

#To install all required packages : pip install -r requirements.txt  or pip3 install -r requirements.txt

now = datetime.now().hour*60 +datetime.now().minute
domain_url = 'https://www.leonard-de-vinci.net/' 
login_url = domain_url + 'ajax.inc.php'
room_url = domain_url + "student/salles/"

user = input("Log in (@edu.devinci.fr) : ")
pw = pwinput()
#user = ''
#pw = ''


def login(session):
    res = session.post(login_url,data = {
        'act':'ident_analyse',
        'login':user,
    })

    if res.status_code == 200:

        #From Joytide repo : https://github.com/Joytide/LDVLogin
        try:
            lssop_endpoint = re.findall(r"\/lssop\/[a-z0-9]*/.*@edu\.devinci\.fr",res.text)[0]
        except:
            print("Unknown user")
            exit(0)
        res = session.get("https://www.leonard-de-vinci.net" + lssop_endpoint, allow_redirects=False)
        SAMLRequest = re.findall(r"(\?SAMLRequest=)(.*)\">",res.text)[0][1]
        res = session.post("https://adfs.devinci.fr/adfs/ls?SAMLRequest="+SAMLRequest.replace("&amp;","&"),
        data = {"UserName": user , "Password" : pw, "AuthMethod" : "FormsAuthentication"},)
        try:
            lssop_endpoint_2 = re.findall(r"(name=\"RelayState\" value=\")(https://www\.leonard-de-vinci\.net/lssop/[0-9a-z]*)\"",res.text)[0][1]
        except:
            print("Wrong user/password combination")
            exit(0)
        SAMLResponse = re.findall(r"(name=\"SAMLResponse\" value=\")(.*)(\" /><input)",res.text)[0][1]
        res = session.get(lssop_endpoint_2)
        m = session.post("https://www.leonard-de-vinci.net/include/SAML/module.php/saml/sp/saml2-acs.php/devinci-sp", data = {"SAMLResponse": SAMLResponse})
        if session:
            print("Logged in as "+user)
        else:
            print("Error while logging in!")
            exit()
        return session
    else:
        print("Error occured")
        exit()

def categories(soup):
    tag = soup.find(id="salle_dpt")
    categories = tag.find_all("option")[1:]

    dict_categories = [{'name':'Tout','checked':True}]
    #dict_categories = ["Tout"]
    for c in categories:
        dict_categories.append({'name':c.string})
        #dict_categories.append(c.string)
    return dict_categories

def printCategories(categories):
    print("Categories disponibles :")
    for k in categories:
        print(f'\t{k} - {categories[k]}')

def correctChoice(choice,categories):
    correct = True
    for c in choice:
        if c not in categories.keys():
            correct = False
            break
    return correct

def choiceToCategory(choices,categories):
    dict = {}
    for c in choices:
        dict[c] = categories[c]
    return dict

def choiceToArray(choices):
    return [k['name'] for k in choices]

def userChoice(categories):
    
    printCategories(categories)

    incorrect = True
    while incorrect: 
        print("Pour plusieurs choix : laissez un espace entre")

        #Revoir pour une vérification des entrées en entier
        choices = [int(choice) for choice in input("Votre choix : ").split()]

        if correctChoice(choices,categories):
            incorrect = False
        else:
            print("Quelque chose s'est mal passée, refaire la saisie...")

    return sorted(choices)

def selectRows(table,choices,categories):
    selected = []
    if choices == ['Tout']:
        #choices = categories
        choices = choiceToArray(categories)


    for rows in table.find_all('tr'):
        rowLabel = rows.th.find_all("span",{'class':'label'})
        if len(rowLabel) > 0:
            if rowLabel[0].string in choices:
                selected.append(rows)
    return selected 

def minutes(time):
    #Convert a string time to minutes (01:00 => 60)
    split = time.split(":")
    return int(split[0])*60 + int(split[1])

def getHours(row):
    hours = []

    rows = row.find_all("td",{'class':'success'})

    if len(rows) > 0:
        for slots in rows:
           
            slot = slots.div.get_text().split("-")

            if len(slot) == 2:
                hours.append(
                    [
                    slot[0], #Début du créneau
                    slot[1]  #Fin du créneau
                    ]
                )
    
    return hours

def getNextCourse(time_now, data_set):

    if (data_set == None):
        return None
    else :
        for slot in data_set:
            if minutes(slot[0]) > time_now:
                return slot[0]
    return None

def minutesLeft(lesser,bigger):
    left = bigger - lesser
    return left

def nowInSlot(time_now,slot_times):

    if len(slot_times) > 0:
 
            start_time = minutes(slot_times[0])
            end_time = minutes(slot_times[1])
            current_time = time_now 

            if start_time <= current_time and end_time >= current_time:
                return True

    return False

def roomIsFreeNow(data_set):
    #For each slots 
    for slots in data_set:
        if nowInSlot(now,slots):
            return False
    return True 

def getRoomNumber(row):
    return row.th.a.string

def getRoomImg(session,row):
    endpoint_attr = row.th.span.find_all('span',{'class':'btn'})

    if len(endpoint_attr) > 0:
        imgTag = BeautifulSoup(endpoint_attr[0].attrs['data-content'],'html.parser')
        endpoint = imgTag.find('img').attrs['src'][2:]
        img_url = room_url + endpoint

        return img_url

    return None

def getRoomInfos(session,row):
    infos = {
        'tag':"ligne", #to replace to row if needed
        'name':getRoomNumber(row),
        'img':getRoomImg(session,row),
        'used_today':False,
    }
    usedToday = row.find_all("td",{'class':'success'})
    if len(usedToday) > 0:
        infos['used_today'] = True
        infos['data_set'] = getHours(row)
        infos['free_now'] = roomIsFreeNow(infos['data_set'])    
        infos['next_course'] = getNextCourse(now,infos['data_set'])
        infos['next_course_in'] = None if infos['next_course'] == None else minutesLeft(now,minutes(infos['next_course']))

    else:
        infos['data_set'] = None
        infos['free_now'] = True
        infos['next_course'] = None
        infos['next_course_in'] = None

    return infos

def room(session,rows): 
    available = {}
    key = 0
    for salle in rows:
        
        key += 1
        available[key] = getRoomInfos(session,salle)

    return available

def formatTime(minutes):
    if minutes == None: return ''
    hourInt = minutes//60
    hour = '' if hourInt == 0 else (str(hourInt) + 'h')

    minutesInt = minutes%60
    minute = str(minutesInt) + 'min'
    return hour + minute

def printAvailable(rooms):
    print("Les salles libres actuellement (" + datetime.now().strftime("%H:%M") + ") sont :")
    print("\t  {0:34} | {1:20} | {2}".format(
                "Nom de la salle",
                "Prochain cours",
                "Image de la salle")
            )
    print(140*"=")
    for available in rooms:
        room = rooms[available]
        if room['free_now']:
            print(
                "\t➜ {0:34} | {1:20} | 📷 {2}".format(
                    room['name'],
                    ('Aucun' if room['next_course'] == None else (room['next_course'] + " (dans " + formatTime(room['next_course_in']) + ")")),
                    ('aucune' if room['img'] == None else room['img'])
                )
            )


if (user == '' and pw == ''):
    with open('credentials.txt','r') as f:
        cred = f.readlines()
        user = cred[0].replace("\n","")
        pw = cred[1].replace("\n","")

with requests.Session() as s:

    s = login(s) 
    res = s.get(room_url)
    soup = BeautifulSoup(res.text, 'html.parser')

    options = categories(soup)

    # questions = [
    #     inquirer.Checkbox(
    #         'categories',
    #         message="Categorie(s) disponible(s) ",
    #         choices=options,
    #         default="Tout",
    #     )
    # ]

    #choices = inquirer.prompt(questions)

    questions = [
       {
           "type": "checkbox",
           "name": "categories",
           "message": "Categories :",
           "choices": options,
       }
    ]

    choices = prompt(questions)

    table = soup.find_all("table",{'class':'table'})[0]
    #rows = selectRows(table,choices["categories"],options[1:])
    rows = selectRows(table,choices["categories"],options)
    rooms = room(s,rows)
    printAvailable(rooms)
