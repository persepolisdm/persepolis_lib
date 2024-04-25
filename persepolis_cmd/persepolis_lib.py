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
from useful_tools import humanReadableSize, convertSize
import sys


class Download():
    def __init__(self, add_link_dictionary, number_of_threads):
        self.downloaded_size = 0
        self.finished_threads = 0
        self.exit_event = threading.Event()

        self.link = add_link_dictionary['link']
        self.name = add_link_dictionary['out']
        self.download_path = add_link_dictionary['download_path']
        self.ip = add_link_dictionary['ip']
        self.port = add_link_dictionary['port']
        self.proxy_user = add_link_dictionary['proxy_user']
        self.proxy_passwd = add_link_dictionary['proxy_passwd']
        self.download_user = add_link_dictionary['download_user']
        self.download_passwd = add_link_dictionary['download_passwd']
        self.header = add_link_dictionary['header']
        self.user_agent = add_link_dictionary['user_agent']
        self.raw_cookies = add_link_dictionary['load_cookies']
        self.referer = add_link_dictionary['referer']

        self.number_of_threads = int(number_of_threads)

    def createSession(self):
        # define a requests session
        self.requests_session = requests.Session()

        if self.ip:
            ip_port = 'http://' + str(self.ip) + ":" + str(self.port)
            if self.proxy_user:
                ip_port = ('http://' + self.proxy_user + ':' +
                           self.proxy_passwd + '@' + ip_port)
            # set proxy to the session
            self.requests_session.proxies = {'http': ip_port}

        if self.download_user:
            # set download user pass to the session
            self.requests_session.auth = (self.download_user,
                                          self.download_passwd)

        # set cookies
        if self.raw_cookies:
            cookie = SimpleCookie()
            cookie.load(self.raw_cookies)

            cookies = {key: morsel.value for key, morsel in cookie.items()}
            self.requests_session.cookies = cookiejar_from_dict(cookies)

        # set referer
        if self.referer:
            # setting referer to the session
            self.requests_session.headers.update({'referer': self.referer})
        # set user_agent
        if self.user_agent:
            # setting user_agent to the session
            self.requests_session.headers.update(
                    {'user-agent': self.user_agent})

    def getFileSize(self):
        response = self.requests_session.head(self.link, allow_redirects=True)
        file_header = response.headers

        # find file size
        try:
            self.file_size = int(file_header['content-length'])
        except Exception as error:
            print(str(error))
            print("Invalid URL")
            self.file_size = None

        return self.file_size, file_header

    def getFileName(self, file_header):
        # set file name
        self.file_name = self.link.split('/')[-1]

        if self.name:
            self.file_name = self.name

        # checking if filename is available
        elif 'Content-Disposition' in file_header.keys():
            content_disposition = file_header['Content-Disposition']

            if content_disposition.find('filename') != -1:

                filename_splited = content_disposition.split('filename=')
                filename_splited = filename_splited[-1]

                # getting file name in desired format
                self.file_name = filename_splited.strip()

    def createFile(self):
        # chunk file
        part_size = int(self.file_size) // self.number_of_threads

        # Create file with size of the content
        if self.download_path:
            self.file_path = os.path.join(self.download_path, self.file_name)
        else:
            self.file_path = self.file_name

        fp = open(self.file_path, "wb")
        fp.write(b'\0' * self.file_size)
        fp.close()

        return part_size

    def runProgressBar(self):
        progress_bar_thread = threading.Thread(
                target=self.progressBar)
        progress_bar_thread.setDaemon(True)
        progress_bar_thread.start()

    def progressBar(self):

        size, unit = humanReadableSize(self.file_size)
        percent = 0
        end_time = time()
        last_download_value = self.downloaded_size
        while (self.finished_threads != self.number_of_threads) and\
                (not (self.exit_event.wait(timeout=0.5))):
            percent = (self.downloaded_size/self.file_size)*100

            converted_downloaded_size = convertSize(self.downloaded_size, unit)
            download_status = (str(round(converted_downloaded_size, 2)) +
                               '|' + str(size) +
                               ' ' + unit)
            filled_up_Length = int(percent / 2)
            bar = ('*' * filled_up_Length +
                   '-' * (50 - filled_up_Length))
            diffrence_time = time() - end_time
            diffrence_size = self.downloaded_size - last_download_value
            diffrence_size_converted, speed_unit = humanReadableSize(
                    diffrence_size, 'speed')
            download_speed = round(diffrence_size_converted / diffrence_time,
                                   2)
            download_speed_str = str(download_speed) + " " + speed_unit + "/s"
            sys.stdout.write('[%s] %s%s ...%s, %s   \r' % (bar,
                                                           int(percent),
                                                           '%',
                                                           download_status,
                                                           download_speed_str))
            sys.stdout.flush()
            end_time = time()
            last_download_value = self.downloaded_size

        if self.finished_threads == self.number_of_threads:
            # cursor up one line
            sys.stdout.write('\x1b[1A')
            # delete last line
            sys.stdout.write('\x1b[2K')
            sys.stdout.write(
                    '[%s] %s%s ...%s, %s   \r' % ('Download complete!',
                                                  int(100),
                                                  '%',
                                                  ('|' + str(size) +
                                                   ' ' + unit),
                                                  self.file_path))
            sys.stdout.flush()

        elif self.exit_event.is_set():
            download_status = (str(round(converted_downloaded_size, 2)) +
                               '|' + str(size) +
                               ' ' + unit)
            # cursor up one line
            sys.stdout.write('\x1b[1A')
            # delete last line
            sys.stdout.write('\x1b[2K')
            sys.stdout.write(
                    '[%s] %s%s ...%s   \n' % ('Download stopped!',
                                              int(percent),
                                              '%',
                                              download_status))
            sys.stdout.write('\x1b[2K')
            sys.stdout.write('  Please wait...\n')
            sys.stdout.flush()

    def runDownloadThreads(self, part_size):
        for i in range(self.number_of_threads):
            start = part_size * i
            end = start + part_size

            # create a Thread with start and end locations
            t = threading.Thread(
                target=self.handler,
                kwargs={'start': start,
                        'end': end})
            t.setDaemon(True)
            t.start()

        # Return the current Thread object
        main_thread = threading.current_thread()

        # Return a list of all Thread objects currently alive
        for t in threading.enumerate():
            if t is main_thread:
                continue
            t.join()

        print('\r', flush=True)

    # The below code is used for each chunk of file handled
    # by each thread for downloading the content from specified
    # location to storage
    def handler(self, start, end):

        # specify the starting and ending of the file
        chunk_headers = {'Range': 'bytes=%d-%d' % (start, end)}

        # request the specified part and get into variable
        self.requests_session.headers.update(chunk_headers)
        r = self.requests_session.get(self.link,
                                      allow_redirects=True, stream=True)

        # open the file and write the content of the html page
        # into file.
        # r+b mode is open the binary file in read or write mode.
        with open(self.file_path, "r+b") as fp:

            fp.seek(start)
            fp.tell()

            for data in r.iter_content(chunk_size=100):
                if not (self.exit_event.is_set()):
                    fp.write(data)
                    self.downloaded_size = self.downloaded_size + 100

        self.finished_threads = self.finished_threads + 1

    def stop(self, signum, frame):
        self.exit_event.set()
