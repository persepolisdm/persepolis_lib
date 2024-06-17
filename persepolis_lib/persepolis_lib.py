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
from time import time
from useful_tools import convertTime, humanReadableSize, convertSize, sendToLog
import sys
import json
from urllib.parse import urlparse, unquote
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class Download():
    def __init__(self, add_link_dictionary, number_of_threads,
                 python_request_chunk_size=1, timeout=15, retry=5):
        self.python_request_chunk_size = python_request_chunk_size
        self.downloaded_size = 0
        self.finished_threads = 0
        self.eta = "0"
        self.resume = False
        self.download_speed_str = "0"
        self.__Version__ = "0.0.1"
        self.download_status = 'pending'
        self.download_finished = False
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
        self.timeout = timeout
        self.retry = retry

    # create requests session
    def createSession(self):
        # define a requests session
        self.requests_session = requests.Session()

        # check if user set proxy
        if self.ip:
            ip_port = 'http://' + str(self.ip) + ":" + str(self.port)
            if self.proxy_user:
                ip_port = ('http://' + self.proxy_user + ':'
                           + self.proxy_passwd + '@' + ip_port)
            # set proxy to the session
            self.requests_session.proxies = {'http': ip_port}

        # check if download session needs authenthication
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

    # get file size
    # if file size is not available, then download link is invalid
    def getFileSize(self):
        response = self.requests_session.head(self.link, allow_redirects=True, timeout=5)
        self.file_header = response.headers

        # find file size
        try:
            self.file_size = int(self.file_header['content-length'])
        except Exception as error:
            print(str(error))
            print("Invalid URL")
            self.file_size = None

        return self.file_size

    # get file name if available
    # if file name is not available, then set a file name
    def getFileName(self):
        # set default file name
        parsed_linkd = urlparse(self.link)
        self.file_name = Path(parsed_linkd.path).name

        # URL might contain percent-encoded characters
        # for example farsi characters in link
        if self.file_name.find('%'):
            self.file_name = unquote(self.file_name)

        # check if user set file name or not
        if self.name:
            self.file_name = self.name

        # check if filename is available in header
        elif 'Content-Disposition' in self.file_header.keys():
            content_disposition = self.file_header['Content-Disposition']

            if content_disposition.find('filename') != -1:

                # so file name is available in header
                filename_splited = content_disposition.split('filename=')
                filename_splited = filename_splited[-1]

                # getting file name in desired format
                self.file_name = filename_splited.strip()

    # this method gives etag from header
    # ETag is an HTTP response header field that helps with caching behavior by making
    # it easy to check whether a resource has changed, without having to re-download it.
    def getFileTag(self):
        if 'ETag' in self.file_header.keys():
            self.etag = self.file_header['ETag']
        else:
            self.etag = None

    # create a file on hard disk equal to downlod file size
    def createFile(self):

        # Divide the file into the number of threads.
        part_size = int(int(self.file_size) // self.number_of_threads)

        # part size must be greater than 1 Mib
        # if size of parts are less than 1 Mib, then change thread numbers
        if part_size <= 1024 * self.python_request_chunk_size:
            # calculate number of threads
            self.number_of_threads = int(self.file_size) // (
                1024 * self.python_request_chunk_size)

            # set thread number to 1 if file size less than 1MiB
            if self.number_of_threads == 0:
                self.number_of_threads = 1
                part_size = self.file_size
            else:
                # recalculate chunk size
                part_size = int(self.file_size) // self.number_of_threads

        # find file_path and control_json_file_path
        # If the file is partially downloaded, the download information is available in the control file.
        # The format of this file is Jason. the control file extension is .persepolis.
        # the control file name is same as download file name.
        # control file path is same as download file path.
        control_json_file = self.file_name + '.persepolis'

        # if user set download path
        if self.download_path:

            self.file_path = os.path.join(self.download_path, self.file_name)
            self.control_json_file_path = os.path.join(
                self.download_path, control_json_file)
        else:
            self.file_path = self.file_name
            self.control_json_file_path = control_json_file

        # create json control file if not created before
        try:
            with open(self.control_json_file_path, 'x') as f:
                f.write("")
        except Exception:
            # so the control file is already exists
            # read control file
            with open(self.control_json_file_path, "r") as f:

                # save json file information in dictionary format
                data_dict = json.load(f)

                # check if the download is duplicated
                # If download item is duplicated, so resume download
                # check ETag
                if 'ETag' in data_dict:

                    if data_dict['ETag'] == self.etag:
                        self.resume = True
                    else:
                        self.resume = False

                # if ETag is not available, then check file size
                elif 'file_size' in data_dict:

                    if data_dict['file_size'] == self.file_size:
                        self.resume = True
                    else:
                        self.resume = False
                else:
                    self.resume = False

        # check if uncomplete download file exists
        if os.path.isfile(self.file_path):
            download_file_existance = True
        else:
            download_file_existance = False

        if self.resume and not (download_file_existance):
            self.resume = False
            create_download_file = True
        elif self.resume and download_file_existance:
            create_download_file = False
        else:
            create_download_file = True

        # create empty file
        if create_download_file:
            fp = open(self.file_path, "wb")
            fp.write(b'\0' * self.file_size)
            fp.close()

        return part_size

    # this method runs progress bar and speed calculator
    def runProgressBar(self):
        # run  a thread for calculating download speed.
        calculate_speed_thread = threading.Thread(
            target=self.downloadSpeed)
        calculate_speed_thread.setDaemon(True)
        calculate_speed_thread.start()

        # run a thread for showing progress bar
        progress_bar_thread = threading.Thread(
            target=self.progressBar)
        progress_bar_thread.setDaemon(True)
        progress_bar_thread.start()

    # this method calculate download speed and ETA every second.
    def downloadSpeed(self):
        # Calculate the difference between downloaded volume and elapsed time
        # and divide them to get the download speed.
        last_download_value = self.downloaded_size
        end_time = time()
        # this loop repeated every 1 second. timeout=1
        # and checks exit_event every time.
        while not (self.download_finished) and\
                (not (self.exit_event.wait(timeout=3))):
            diffrence_time = time() - end_time
            diffrence_size = self.downloaded_size - last_download_value
            diffrence_size_converted, speed_unit = humanReadableSize(
                diffrence_size, 'speed')
            download_speed = round(diffrence_size_converted / diffrence_time,
                                   2)
            self.download_speed_str = (str(download_speed)
                                       + " " + speed_unit + "/s")
            not_converted_download_speed = diffrence_size / diffrence_time
            try:
                # estimated time the download will be completed.
                eta_second = (self.file_size
                              - self.downloaded_size) /\
                    not_converted_download_speed
            except Exception:
                eta_second = 0

            self.eta = convertTime(eta_second)
            end_time = time()
            last_download_value = self.downloaded_size

    # this method shows progress bar
    def progressBar(self):

        size, unit = humanReadableSize(self.file_size)
        percent = 0
        while not (self.download_finished) and\
                (not (self.exit_event.wait(timeout=0.5))):
            percent = (self.downloaded_size / self.file_size) * 100

            converted_downloaded_size = convertSize(self.downloaded_size, unit)
            download_status = (str(round(converted_downloaded_size, 2))
                               + '|' + str(size)
                               + ' ' + unit)
            filled_up_Length = int(percent / 2)
            bar = ('*' * filled_up_Length
                   + '-' * (50 - filled_up_Length))

            # find downloded size of every thread
#             downloaded_size_list_str = ""
#             for i in range(len(self.downloaded_size_list)):
#                 part_size_converted, unit_part_size = humanReadableSize(
#                         self.downloaded_size_list[i])
#                 downloaded_size_list_str = (
#                         downloaded_size_list_str +
#                         "part " +
#                         str(i + 1) +
#                         ": " +
#                         str(part_size_converted) +
#                         unit_part_size +
#                         "|")
#                 if i in list(range(3, 31, 4)):
#                     downloaded_size_list_str = downloaded_size_list_str + '\n'
            downloaded_size_list_str = ""
            for i in range(len(self.response_list)):
                downloaded_size_list_str = (
                    downloaded_size_list_str
                    + "part "
                    + str(i + 1)
                    + ": "
                    + str(self.response_list[i])
                    + "|")
                if i in list(range(3, 31, 4)):
                    downloaded_size_list_str = downloaded_size_list_str + '\n'

            downloaded_size_list_str = downloaded_size_list_str + "\n"
            number_of_lines = downloaded_size_list_str.count("\n")
            active_connection = self.number_of_threads - self.finished_threads
            # delete last line
            sys.stdout.write(
                '[%s] %s%s ...%s, %s |connections:%s|ETA:%s\n%s' % (
                    bar,
                    int(percent),
                    '%',
                    download_status,
                    self.download_speed_str,
                    active_connection,
                    self.eta,
                    downloaded_size_list_str))

            sys.stdout.flush()

            # move curser to the first line and clear screen
            for i in list(range(number_of_lines + 1)):
                sys.stdout.write('\x1b[1A')
                sys.stdout.write('\x1b[2K')

        # print download complete message
        if self.downloaded_size == self.file_size:
            # cursor up one line
            sys.stdout.write('\x1b[1A')
            # delete last line
            sys.stdout.write('\x1b[2K')
            sys.stdout.write(
                '[%s] %s%s ...%s, %s   \r' % ('Download complete!',
                                              int(100),
                                              '%',
                                              ('|' + str(size)
                                                   + ' ' + unit),
                                              self.file_path))
            sys.stdout.flush()

        elif self.exit_event.is_set():
            download_status = (str(round(converted_downloaded_size, 2))
                               + '|' + str(size)
                               + ' ' + unit)
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

    # this method runs download threads
    def runDownloadThreads(self, part_size):

        # Resume the incomplete download.
        if self.resume:
            # read control file
            with open(self.control_json_file_path, "r") as f:
                data_dict = json.load(f)

            # read number of threads
            self.number_of_threads = data_dict['number_of_threads']
            # read start of every chunk.
            self.start_of_chunks_list = data_dict['start_of_chunks_list']
            # Read the amount downloaded for each thread.
            self.downloaded_size_list = data_dict['downloaded_size_list']
            # calculate downloaded size
            self.downloaded_size = sum(self.downloaded_size_list)

        # start new download
        else:
            # create a list for saving amount of downloads for every thread
            self.downloaded_size_list = [0] * self.number_of_threads

            # this list saves start of chunks
            self.start_of_chunks_list = [0] * self.number_of_threads

            # set the start byte number for every thread
            for i in (range(self.number_of_threads)):
                self.start_of_chunks_list[i] = part_size * i

        # this list saves response of python request for every threads
        # save the answers for errors or to check the completion of the threads process.
        self.response_list = [0] * self.number_of_threads

        # this list saves status of threads
        # 4 situation: active, error, complete, stopped
        self.thread_status_list = ['active'] * self.number_of_threads

        # set start and end of all parts except the last one
        for i in (range(self.number_of_threads - 1)):
            if self.resume:
                if self.downloaded_size_list[i] != 0:
                    start = (self.start_of_chunks_list[i]
                             + self.downloaded_size_list[i])
                else:
                    start = part_size * i

            else:
                start = self.start_of_chunks_list[i]

            end = part_size * (i + 1)
            # create a Thread with start and end locations
            # thread_number is between 0 and number_of_threads - 1
            t = threading.Thread(
                target=self.handler,
                kwargs={'start': start,
                        'end': end,
                        'thread_number': i})
            t.setDaemon(True)
            t.start()

        # last thread!
        # end of last part must be set to the end of the file
        # so the last byte value is equal to the file_size
        if self.resume:
            start = (self.start_of_chunks_list[(self.number_of_threads - 1)]
                     + self.downloaded_size_list[(self.number_of_threads - 1)])

        else:
            start = part_size * (self.number_of_threads - 1)
            self.start_of_chunks_list[(self.number_of_threads - 1)] = start

        end = self.file_size

        # create a Thread with start and end locations
        t = threading.Thread(
            target=self.handler,
            kwargs={'start': start,
                    'end': end,
                    'thread_number': (self.number_of_threads - 1)})
        t.setDaemon(True)
        t.start()

        # run saveInfo thread for updating control file
        save_control_thread = threading.Thread(
            target=self.saveInfo)
        save_control_thread.setDaemon(True)
        save_control_thread.start()

        # TODO
        # checking connections while download process is not complete or stopped
        # wait(timeout=1) works as time.sleep(1)
        # change retry_done to True if retrying is done.
        retry_number = 0
        while (self.file_size != self.downloaded_size) and\
                (not (self.exit_event.wait(timeout=1))):

            # if threads status is not active or stopped
            # so threads finished download with complete or error status
            if 'active' not in self.thread_status_list:
                if 'stopped' not in self.thread_status_list:
                    sendToLog('thread_status_list: ' + str(self.thread_status_list))

                    # Don't retry again if retry_number is equal to self.retry
                    if retry_number == self.retry:
                        self.download_status = 'Error'
                        sendToLog('Stop retrying ' + str(retry_number))
                        break

                    # retry
                    for thread_index, thread_status in enumerate(self.thread_status_list):
                        if thread_status == 'error':

                            # restart thread
                            # find start and end of part and set new start
                            # new start is start + downloaded_part
                            start = (self.start_of_chunks_list[thread_index]
                                     + self.downloaded_size_list[thread_index])

                            if thread_index != (self.number_of_threads - 1):
                                end = self.start_of_chunks_list[thread_index + 1] - 1
                            else:
                                # last thread
                                end = self.file_size

                            # set active status for thread
                            self.thread_status_list[thread_index] = 'active'
                            self.finished_threads = self.finished_threads - 1

                            # create a Thread with start and end locations
                            t = threading.Thread(
                                target=self.handler,
                                kwargs={'start': start,
                                        'end': end,
                                        'thread_number': thread_index})
                            t.setDaemon(True)
                            t.start()

                    sendToLog('retry_number is ' + str(retry_number))
                    retry_number = retry_number + 1

            # download process ends
        self.download_finished = True
        # Return the current Thread object
        main_thread = threading.current_thread()

        # Return a list of all Thread objects currently alive
        for t in threading.enumerate():
            if t is main_thread:
                continue
            t.join()

        print('\r', flush=True)
        self.requests_session.close()

    # The below code is used for each chunk of file handled
    # by each thread for downloading the content from specified
    # location to storage
    def handler(self, start, end, thread_number):

        try:
            # calculate part size
            if thread_number != (self.number_of_threads - 1):
                part_size = self.start_of_chunks_list[thread_number + 1] - self.start_of_chunks_list[thread_number]
            else:
                # for the last part
                part_size = self.file_size - self.start_of_chunks_list[thread_number]

            # amount of downlded size from this part is saved
            # in this variable
            downloaded_part = self.downloaded_size_list[thread_number]

            # specify the starting and ending of the file
            chunk_headers = {'Range': 'bytes=%d-%d' % (start, end)}

            # request the specified part and get into variable
            self.requests_session.headers.update(chunk_headers)
            response = self.requests_session.get(
                self.link, allow_redirects=True, stream=True,
                timeout=self.timeout)

            # save response to response_list
            self.response_list[thread_number] = response.status_code

            # open the file and write the content of the html page
            # into file.
            # r+b mode is open the binary file in read or write mode.
            with open(self.file_path, "r+b") as fp:

                fp.seek(start)
                fp.tell()

                # why we use iter_content
                # Iterates over the response data. When stream=True is set on
                # the request, this avoids reading the content at once into
                # memory for large responses. The chunk size is the number
                # of bytes it should read into memory. This is not necessarily
                # the length of each item returned as decoding can take place.
                # so we divide our chunk to smaller chunks. default is 1 Mib
                python_request_chunk_size = (1024
                                             * self.python_request_chunk_size)
                for data in response.iter_content(
                        chunk_size=python_request_chunk_size):
                    if not (self.exit_event.is_set()):
                        fp.write(data)

                        # maybe the last chunk is less than 1MiB(default chunk size)
                        if downloaded_part <= (part_size
                                               - python_request_chunk_size):
                            update_chunk_size = python_request_chunk_size
                        else:
                            # so the last small chunk is equal to :
                            update_chunk_size = (part_size - downloaded_part)

                        # update downloaded_part
                        downloaded_part = (downloaded_part
                                           + update_chunk_size)
                        # save value to downloaded_size_list
                        self.downloaded_size_list[
                            thread_number] = downloaded_part

                        # this variable saves amount of total downloaded size
                        # update downloaded_size
                        self.downloaded_size = (self.downloaded_size
                                                + update_chunk_size)
                    else:
                        # exit_event is set
                        self.thread_status_list[thread_number] = 'stopped'
                        break

        except requests.ConnectionError as e:
            # backoff_factor will help to apply delays between attempts to avoid failing again
            retry = Retry(connect=3, backoff_factor=5)
            adapter = HTTPAdapter(max_retries=retry)
            self.requests_session.mount('http://', adapter)
            self.requests_session.mount('https://', adapter)

            self.thread_status_list[thread_number] = 'error'
            error_text = ("thread_number: "
                          + str(thread_number)
                          + " " + str(e))
            sendToLog(error_text)

        except Exception as e:
            self.thread_status_list[thread_number] = 'error'
            error_text = ("thread_number: "
                          + str(thread_number)
                          + " " + str(e))
            sendToLog(error_text)

        # if thread status ends with active status
        # so it's complete successfully.
        if (self.thread_status_list[thread_number] == 'active') and (self.downloaded_size_list[thread_number] == part_size):
            sendToLog('thread ' + str(thread_number) + ' is complete!')
            self.thread_status_list[thread_number] = 'complete'
        else:
            self.thread_status_list[thread_number] = 'error'

        self.finished_threads = self.finished_threads + 1

    # this method save download information in json format every 1 second
    def saveInfo(self):
        while (self.finished_threads != self.number_of_threads) and\
                (not (self.exit_event.wait(timeout=1))):
            control_dict = {
                'ETag': self.etag,
                'file_name': self.file_name,
                'file_size': self.file_size,
                'number_of_threads': self.number_of_threads,
                'start_of_chunks_list': self.start_of_chunks_list,
                'downloaded_size_list': self.downloaded_size_list}

            # write control_dict in json file
            with open(self.control_json_file_path, "w") as outfile:
                json.dump(control_dict, outfile)

    # this method starts download
    def start(self):
        self.createSession()
        file_size = self.getFileSize()
        if file_size:
            self.getFileName()

            self.getFileTag()

            part_size = self.createFile()

            self.runProgressBar()

            self.runDownloadThreads(part_size)
        self.close()

    def stop(self, signum, frame):
        self.download_status = 'Stopped'
        self.exit_event.set()

    def close(self):
        # if download complete, so delete control file
        if self.downloaded_size == self.file_size:
            self.download_status = 'Complete'
            os.remove(self.control_json_file_path)

        # delete last line
        sys.stdout.write('\x1b[2K')
        if self.download_status == 'Stopped':
            sys.stdout.write('  Download stopped!\n')
        elif self.download_status == 'Error':
            sys.stdout.write('  Error\n')
        sys.stdout.write('  Persepolis CMD is closed!\n')
        sys.stdout.flush()
