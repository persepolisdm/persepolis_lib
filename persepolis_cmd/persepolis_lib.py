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

# The below code is used for each chunk of file handled
# by each thread for downloading the content from specified
# location to storage
def handler(start, end, link, file_path, requests_session):

    # specify the starting and ending of the file
    chunk_headers = {'Range': 'bytes=%d-%d' % (start, end)}

    requests_session.headers.update(chunk_headers)

    # request the specified part and get into variable
    r = requests_session.get(link, stream=True)

    # open the file and write the content of the html page
    # into file.
    # r+b mode is open the binary file in read or write mode.
    with open(file_path, "r+b") as fp:

        fp.seek(start)
        fp.tell()
        fp.write(r.content)

def downloadFile(add_link_dictionary, number_of_threads): 

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

    requests_session.allow_redirects = True


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


    response = requests.head(link) 
    file_header = response.headers

    # find file size
    try: 
        file_size = int(file_header['content-length']) 
    except: 
        print("Invalid URL")
        return


    # set file name
    if name: 
        file_name = name 

    elif 'Content-Disposition' in file_header.keys():  # checking if filename is available

        content_disposition = file_header['Content-Disposition']

        if content_disposition.find('filename') != -1:

            filename_splited = content_disposition.split('filename=')
            filename_splited = filename_splited[-1]

            # getting file name in desired format
            file_name = filename_splited.strip() 
    else:
        file_name = link.split('/')[-1] 


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
