from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pprint,os,requests

from urllib.parse import urlparse, parse_qs, unquote

options = Options()
options.add_experimental_option("prefs", {
    "download.default_directory": "/home/d/Hämtningar/learn.du.se",
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True,
    "profile.default_content_setting_values.automatic_downloads": 2,
    "plugins.always_open_pdf_externally": True
})

browser = webdriver.Chrome(chrome_options=options, desired_capabilities=d)
browser.get('https://learn.du.se/ultra')

browser.find_element_by_id('username').send_keys('iwconfig')
browser.find_element_by_id('password').send_keys('plz hack me')
browser.find_element_by_class_name('btn-submit').click()

browser.get('https://learn.du.se/webapps/blackboard/content/listContent.jsp?course_id=_2148_1&content_id=_128691_1&mode=reset')

cookies = browser.get_cookies()
r = requests.Session()
for cookie in cookies:
    r.cookies.set(cookie['name'], cookie['value'])

blah = []
elements = browser.find_elements_by_class_name("item")
delkurser = {}

for x in elements:
    if x.text == 'Filosofisk metod och kritiskt tänkande':
        continue
    delkurser[x.text] = {'url': x.find_element_by_tag_name('a').get_attribute('href')}

for k,v in delkurser.items():
    browser.get(v['url'])
    v['moment'],v['moment']['files'] = ({},{})
    for moment in browser.find_elements_by_class_name("item"):
        if moment.find_element_by_tag_name('a').get_attribute('onclick'):
            v['moment']['files'].update({moment.text: moment.find_element_by_tag_name('a').get_attribute('href')})
        else:
            v['moment'].update({moment.text: moment.find_element_by_tag_name('a').get_attribute('href')})
    browser.back()

# for k,v in delkurser.items():

#     for name,url in v['moment'].items():
#         print(url)
#         if isinstance(url, dict):
#             for NAME,URL in url.items():
#                 print('DOWNLOADING: ', NAME)
#                 PATH = '/home/d/Hämtningar/learn.du.se/{}/{}'.format(k, NAME)
#                 os.makedirs(PATH,exist_ok=True)
#                 URL = r.get(URL).url
#                 o = urlparse(URL)
#                 #query = parse_qs(o.query)
#                 #print(o)
#                 FILE_NAME = unquote(os.path.basename(o.path))
#                 print(os.path.join(PATH, FILE_NAME))
#                 #print(query)
#                 R = r.get(URL)
#                 #R.headers
#                 if R.status_code == 200:
#                     if 'text/html' in R.headers['Content-Type']:
#                         match = re.findall('playlist(High|Low)\.push\((.*)\);', R.text)
#                         for x in match:
#                             x = ast.literal_eval(x[1] if x[0] == 'High' else x[1])
#                             print(x)
#                             for y in x['sources']:
#                                 url = y['file']
#                                 cmd = './youtube-dl {} -o'.format(url).split()
#                                 cmd.append('{0}{1}.mp4'.format(PATH, ' - {}'.format(x['title']) if x['title'] else ''))
#                                 out = subprocess.check_output(cmd)
#                                 print(out)
#                     else:
#                         with open(os.path.join(PATH, FILE_NAME), 'wb') as f:
#                             f.write(R.content)

#                 #download(URL, PATH)

#                 #browser.get(URL)
#                 #if browser.find_elements_by_css_selector('#download'):
#                 #    browser.find_elements_by_css_selector('#download').click()
#                 #browser.back()
#         else:
#             browser.get(url)
#             for f in browser.find_elements_by_class_name("item"):
#                 v['moment']['files'].update({f.text: f.find_element_by_tag_name('a').get_attribute('href')})
#         browser.back()


pp = pprint.PrettyPrinter(indent=4)
pp.pprint(delkurser)

#for idx, kurs in enumerate(elements):
#   browser.execute_script("window.open()")
#   browser.switch_to.window(browser.window_handles[idx])
#   browser.get(kurs.find_element_by_tag_name('a').get_attribute('href'))
#   delar = browser.find_elements_by_class_name("item")
#   backurl = browser.current_url
#   print(backurl)
#   for moment in delar:
#       url = moment.find_element_by_tag_name('a').get_attribute('href')
#       browser.get(url)
#       print(url, 'MOMENT')
#       links = browser.find_elements_by_class_name("item")
#       for el in links:
#           print(el.find_element_by_tag_name('a').get_attribute('href'), 'ELEMENT')
#           #elements = browser.find_elements_by_class_name("item")
#       browser.get(backurl)
#       print(moment)
#   browser.get('https://learn.du.se/webapps/blackboard/content/listContent.jsp?course_id=_2148_1&content_id=_128691_1&mode=reset')
#print(blah)
