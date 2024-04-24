# -*- coding: utf-8 -*-

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


# this script forked from 
# https://www.geeksforgeeks.org/simple-multithreaded-download-manager-in-python/


import requests
import threading 
import os
from requests.cookies import cookiejar_from_dict
from http.cookies import SimpleCookie
from time import sleep, time
import sys

global downloaded_size
global finished_threads

# this function converts file_size to KiB or MiB or GiB
def humanReadableSize(size, input_type='file_size'): 
    labels = ['KiB', 'MiB', 'GiB', 'TiB']
    i = -1
    if size < 1024:
        return size , 'B'

    while size >= 1024:
        i += 1
        size = size / 1024
        
    if input_type == 'speed':
        j = 0
    else:
        j = 1

    if i > j:
        return round(size, 2), labels[i]
    else:
        return round(size, None), labels[i]

def convertSize(size, unit):
    if unit == 'B':
        converted_size = size
    elif unit == 'KiB':
        converted_size = size / 1024
    elif unit == 'MiB':
        converted_size = size / 1024**2
    elif unit == 'GiB':
        converted_size = size / 1024**3
    elif unit == 'TiB':
        converted_size = size / 1024**4

    return converted_size

def progressBar(file_size, number_of_threads):
    global downloaded_size
    global finished_threads

    size, unit = humanReadableSize(file_size)
    percent = 0
    end_time = time()
    last_download_value = downloaded_size
    while finished_threads != number_of_threads:
        percent = (downloaded_size/file_size)*100 
        bar_length = 100
        converted_downloaded_size = convertSize(downloaded_size, unit)
        download_status = str(round(converted_downloaded_size, 2)) + '|' + str(size) + ' ' + unit
        filled_up_Length = int(round(bar_length* percent / float(100)))
        bar = '=' * filled_up_Length + '-' * (bar_length - filled_up_Length)
        diffrence_time = time() - end_time
        diffrence_size = downloaded_size - last_download_value
        diffrence_size_converted, speed_unit = humanReadableSize(diffrence_size, 'speed')
        download_speed = round(diffrence_size_converted / diffrence_time, 2)
        download_speed_str = str(download_speed) + " " + speed_unit + "/s"
        sys.stdout.write('[%s] %s%s ...%s, %s   \r' %(bar, int(percent), '%', download_status, download_speed_str))
        sys.stdout.flush() 
        end_time = time()
        last_download_value = downloaded_size
        sleep(0.5)


# The below code is used for each chunk of file handled
# by each thread for downloading the content from specified
# location to storage
def handler(start, end, link, file_path, requests_session):

    global downloaded_size
    global finished_threads

    # specify the starting and ending of the file
    chunk_headers = {'Range': 'bytes=%d-%d' % (start, end)}

    # request the specified part and get into variable
    r = requests_session.get(link, headers=chunk_headers, allow_redirects=True, stream=True)

    # open the file and write the content of the html page
    # into file.
    # r+b mode is open the binary file in read or write mode.
    with open(file_path, "r+b") as fp:

        fp.seek(start)
        fp.tell()

        for data in r.iter_content(chunk_size=100):
            fp.write(data)
            downloaded_size = downloaded_size + 100


#         fp.write(r.content)
    finished_threads = finished_threads + 1

def downloadFile(add_link_dictionary, number_of_threads): 
    global downloaded_size
    global finished_threads
    downloaded_size = 0
    finished_threads = 0

    link = add_link_dictionary['link']
    name = add_link_dictionary['out']
    download_path = add_link_dictionary['download_path']
    ip = add_link_dictionary['ip']
    port = add_link_dictionary['port']
    proxy_user = add_link_dictionary['proxy_user']
    proxy_passwd = add_link_dictionary['proxy_passwd']
    download_user = add_link_dictionary['download_user']
    download_passwd = add_link_dictionary['download_passwd']
    header = add_link_dictionary['header']
    user_agent = add_link_dictionary['user_agent']
    raw_cookies = add_link_dictionary['load_cookies']
    referer = add_link_dictionary['referer']

    number_of_threads = int(number_of_threads)
    
    # define a requests session
    requests_session = requests.Session()


    if ip:
        ip_port = 'http://' + str(ip) + ":" + str(port)
        if proxy_user:
            ip_port = 'http://' + proxy_user + ':' + proxy_passwd + '@' + ip_port
        # set proxy to the session
        requests_session.proxies = {'http': ip_port}

    if download_user:
        # set download user pass to the session
        requests_session.auth = (download_user, download_passwd)

    # set cookies
    if raw_cookies:
        cookie = SimpleCookie()
        cookie.load(raw_cookies)

        cookies = {key: morsel.value for key, morsel in cookie.items()}
        requests_session.cookies = cookiejar_from_dict(cookies)

    # set referer
    if referer:
        requests_session.headers.update({'referer': referer})  # setting referer to the session

    # set user_agent
    if user_agent:
        requests_session.headers.update({'user-agent': user_agent})  # setting user_agent to the session


    response = requests.head(link, allow_redirects=True) 
    file_header = response.headers

    # find file size
    try: 
        file_size = int(file_header['content-length']) 
    except: 
        print("Invalid URL")
        return


    # set file name
    file_name = link.split('/')[-1] 


    if name: 
        file_name = name 

    elif 'Content-Disposition' in file_header.keys():  # checking if filename is available

        content_disposition = file_header['Content-Disposition']

        if content_disposition.find('filename') != -1:

            filename_splited = content_disposition.split('filename=')
            filename_splited = filename_splited[-1]

            # getting file name in desired format
            file_name = filename_splited.strip() 

    # chunk file
    part = int(file_size) // number_of_threads

    # Create file with size of the content
    if download_path:
        file_path = os.path.join(download_path, file_name) 
    else:
        file_path = file_name

    fp = open(file_path, "wb")
    fp.write(b'\0' * file_size)
    fp.close()

    progress_bar_thread = threading.Thread(target=progressBar,
                         kwargs={'file_size': file_size,
                                 'number_of_threads': number_of_threads})
    progress_bar_thread.setDaemon(True)
    progress_bar_thread.start()


    for i in range(number_of_threads):
        start = part * i
        end = start + part

        # create a Thread with start and end locations
        t = threading.Thread(target=handler,
                             kwargs={'start': start,
                                     'end': end,
                                     'link': link,
                                     'file_path': file_path,
                                     'requests_session': requests_session})
        t.setDaemon(True)
        t.start()


    # Return the current Thread object
    main_thread = threading.current_thread()

    # Return a list of all Thread objects currently alive
    for t in threading.enumerate():
        if t is main_thread:
            continue
        t.join()
    print('%s downloaded'  % file_name)
