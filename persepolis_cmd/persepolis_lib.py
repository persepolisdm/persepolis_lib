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


import requests
import threading 
import os

# this script forked from 
# https://www.geeksforgeeks.org/simple-multithreaded-download-manager-in-python/

# The below code is used for each chunk of file handled
# by each thread for downloading the content from specified
# location to storage
def handler(start, end, url, file_path):

    # specify the starting and ending of the file
    headers = {'Range': 'bytes=%d-%d' % (start, end)}

    # request the specified part and get into variable
    r = requests.get(url, headers=headers, stream=True, allow_redirects=True)

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
    number_of_threads = int(number_of_threads)
    
    response = requests.head(link, allow_redirects=True) 
    header = response.headers
    # find file size
    try: 
        file_size = int(response.headers['content-length']) 
    except: 
        print("Invalid URL")
        return


    # set file name
    if name: 
        file_name = name 

    elif 'Content-Disposition' in header.keys():  # checking if filename is available

        content_disposition = header['Content-Disposition']

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
    file_path = os.path.join(download_path, file_name) 
    fp = open(file_path, "wb")
    fp.write(b'\0' * file_size)
    fp.close()


    for i in range(number_of_threads):
        start = part * i
        end = start + part

        # create a Thread with start and end locations
        t = threading.Thread(target=handler,
                             kwargs={'start': start, 'end': end, 'url': link, 'file_path': file_path})
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
