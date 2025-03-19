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
import time
import random
import threading
import os
import errno
from persepolis_lib.useful_tools import convertTime, humanReadableSize, convertSize, sendToLog, convertHeaderToDictionary, readCookieJar, getFileNameFromLink
import sys
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class Download():
    def __init__(self, add_link_dictionary, number_of_threads=64,
                 python_request_chunk_size=100, timeout=5, retry=5, progress_bar=False, threads_progress_bar=False):
        self.python_request_chunk_size = python_request_chunk_size
        self.progress_bar = progress_bar
        self.threads_progress_bar = threads_progress_bar
        self.downloaded_size = 0
        self.finished_threads = 0
        self.eta = "0"
        self.resume = False
        self.download_speed_str = "0"
        self.__Version__ = "1.0.3"

        # download_status can be in waiting, downloading, stop, error, paused
        self.download_status = 'waiting'
        self.file_name = '***'
        self.file_size = 0

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
        self.load_cookies = add_link_dictionary['load_cookies']
        self.referer = add_link_dictionary['referer']
        self.proxy_type = add_link_dictionary['proxy_type']
        self.number_of_parts = 0
        self.timeout = timeout
        self.retry = retry
        self.lock = False
        self.sleep_for_speed_limiting = 0
        self.not_converted_download_speed = 0
        self.download_percent = 0

        # number_of_threads can't be more that 64
        if number_of_threads <= 64:
            self.number_of_threads = int(number_of_threads)
        else:
            self.number_of_threads = 64

        self.number_of_active_connections = self.number_of_threads

        self.thread_list = []

        # this dictionary contains information about Each part is downloaded by which thread.
        self.part_thread_dict = {}

    # create requests session
    def createSession(self):
        # define a requests session
        self.requests_session = requests.Session()

        # check if user set proxy
        if self.ip:
            ip_port = '://' + str(self.ip) + ":" + str(self.port)
            if self.proxy_user:
                ip_port = ('://' + self.proxy_user + ':'
                           + self.proxy_passwd + '@' + ip_port)
            if self.proxy_type == 'socks5':
                ip_port = 'socks5' + ip_port
            else:
                ip_port = 'http' + ip_port

            proxies = {'http': ip_port,
                       'https': ip_port}

            # set proxy to the session
            self.requests_session.proxies.update(proxies)

        # set cookies
        if self.load_cookies:
            jar = readCookieJar(self.load_cookies)
            if jar:
                self.requests_session.cookies = jar

        # set referer
        if self.referer:
            # setting referer to the session
            self.requests_session.headers.update({'referer': self.referer})

        # set user_agent
        if self.user_agent:
            # setting user_agent to the session
            self.requests_session.headers.update(
                {'user-agent': self.user_agent})
        else:
            self.user_agent = 'Persepolis lib/' + self.__Version__
            # setting user_agent to the session
            self.requests_session.headers.update(
                {'user-agent': self.user_agent})

        if self.header is not None:
            # convert header to dictionary
            dict_ = convertHeaderToDictionary(self.header)
            # update headers
            self.requests_session.headers.update(dict_)

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

    def setRetry(self):
        # set retry numbers.
        # backoff_factor will help to apply delays between attempts to avoid failing again
        retry = Retry(connect=self.retry, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retry)
        self.requests_session.mount('http://', adapter)
        self.requests_session.mount('https://', adapter)

    # get file name if available
    # if file name is not available, then set a file name
    def getFileName(self):
        # set default file name
        # get file name from link string.
        self.file_name = getFileNameFromLink(self.link)

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

    # Check if server supports multi threading or not
    def multiThreadSupport(self):
        if 'Accept-Ranges' in self.file_header.keys():
            if self.file_header['Accept-Ranges'] == 'bytes':
                sendToLog('Server supports multi thread downloading!')
                return True
            else:
                sendToLog('Server dosn\'t support multi thread downloading!')
                return False

    def createControlFile(self):
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
        except OSError as e:
            # it means control_json_file_path characters is more than 256 byte
            if e.errno == errno.ENAMETOOLONG:
                # reduce  file_name lenght
                reduce_bytes = len(self.control_json_file_path.encode('utf-8')) - 255

                # seperate extension from file_name
                split_file_name = self.file_name.split('.')

                # check we have extension or not
                extension = ""
                if len(split_file_name) > 1:
                    # remove extension
                    extension = split_file_name.pop(-1)

                # join file_name without extension
                file_name_without_extension = ''.join(split_file_name)

                if len(file_name_without_extension.encode('utf-8')) > reduce_bytes:

                    # Calculate how many characters must be removed
                    for i in range(len(file_name_without_extension)):
                        string_ = file_name_without_extension[(-1 * i):]
                        string_size = len(string_.encode('utf-8'))
                        if string_size >= reduce_bytes:
                            # reduce characters
                            file_name_without_extension = file_name_without_extension[:(-1 * i)]
                            break

                    # create new file_name and file_path and control_json_file
                    self.file_name = file_name_without_extension + extension
                    self.file_path = os.path.join(self.download_path, self.file_name)
                    control_json_file = self.file_name + '.persepolis'
                    self.control_json_file_path = os.path.join(
                        self.download_path, control_json_file)

                # try again
                with open(self.control_json_file_path, 'x') as f:
                    f.write("")

            else:
                # so the control file is already exists
                # read control file
                with open(self.control_json_file_path, "r") as f:

                    try:
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

                    # control file is corrupted.
                    except Exception:
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

    def definePartSizes(self):
        # download_infromation_list contains 64 lists.
        # Every list contains:
        # [start byte number for this part, downloaded size, download status for this part, number of retryingfor this part]
        # Status can be stopped, pending, downloading, error, complete
        # All part statuses start with a lowercase letter.
        # Retry number is -1, because askForNewPart method add 1 to it in the first call.
        if self.resume:
            # read control file
            with open(self.control_json_file_path, "r") as f:
                data_dict = json.load(f)

            # read number of threads
            self.download_infromation_list = data_dict['download_infromation_list']

            # read number_of_parts
            self.number_of_parts = data_dict['number_of_parts']

            # set pending status for uncomplete parts
            for i in range(0, 64):
                if self.download_infromation_list[i][2] != 'complete':
                    self.download_infromation_list[i] = [self.download_infromation_list[i][0], self.download_infromation_list[i][1], 'pending', -1]

                self.downloaded_size = self.downloaded_size + self.download_infromation_list[i][1]
        else:
            part_size = int(self.file_size // 64)
            # create new list.
            self.download_infromation_list = [[]] * 64

            # if part_size greater than 1 MiB
            if part_size >= 1024**2:
                self.number_of_parts = 64
                for i in range(0, 64):
                    self.download_infromation_list[i] = [i * part_size, 0, 'pending', -1]

            else:
                # Calculate how many parts of one MiB we need.
                self.number_of_parts = int(self.file_size // (1024**2)) + 1
                self.number_of_threads = self.number_of_parts
                for i in range(0, self.number_of_parts):
                    self.download_infromation_list[i] = [i * 1024 * 1024, 0, 'pending', -1]

                # Set the starting byte number of the remaining parts equal to the size of the file.
                # The size of the file is equal to the last byte of the file.
                # The status of these parts is complete. Because we have nothing to download.
                for i in range(self.number_of_parts, 64):
                    self.download_infromation_list[i] = [self.file_size, 0, 'complete', -1]

        for i in range(0, self.number_of_parts):
            self.part_thread_dict[i] = None

    # this method calculates download rate and ETA every second
    # and alculates sleep between data reception for limiting download rate.
    def downloadSpeed(self):
        # Calculate the difference between downloaded volume and elapsed time
        # and divide them to get the download speed.
        last_download_value = self.downloaded_size
        end_time = time.perf_counter()
        # this loop repeated every 5 second.
        while self.download_status == 'downloading' or self.download_status == 'paused':
            diffrence_time = time.perf_counter() - end_time
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

            end_time = time.perf_counter()
            last_download_value = self.downloaded_size

            time.sleep(5)

    # this method shows progress bar
    def progressBar(self):

        size, unit = humanReadableSize(self.file_size)
        percent = 0
        while (self.download_status == 'downloading' or self.download_status == 'paused'):
            time.sleep(0.5)
            percent = (self.downloaded_size / self.file_size) * 100

            converted_downloaded_size = convertSize(self.downloaded_size, unit)
            show_download_information = (str(round(converted_downloaded_size, 2))
                                         + '|' + str(size)
                                         + ' ' + unit)
            filled_up_Length = int(percent / 2)
            bar = ('*' * filled_up_Length
                   + '-' * (50 - filled_up_Length))

            # find downloded size of every part
            downloaded_size_list_str = ""
            if self.threads_progress_bar is True:
                for i in range(0, 64):
                    part_size_converted, unit_part_size = humanReadableSize(
                        self.download_infromation_list[i][1])
                    downloaded_size_list_str = (
                        downloaded_size_list_str
                        + "part "
                        + str(i + 1)
                        + ": "
                        + str(part_size_converted)
                        + unit_part_size
                        + "|")
                    if i in list(range(3, 64, 4)):
                        downloaded_size_list_str = downloaded_size_list_str + '\n'
                downloaded_size_list_str = downloaded_size_list_str + "\n"
                number_of_lines = downloaded_size_list_str.count("\n")
            else:
                number_of_lines = 0

            # number os active threads
            active_connection = self.number_of_threads - self.finished_threads

            # delete last line
            sys.stdout.write(
                '[%s] %s%s ...%s, %s |connections:%s|ETA:%s\n%s' % (
                    bar,
                    int(percent),
                    '%',
                    show_download_information,
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
        if self.download_status == 'complete':
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

        elif self.download_status == 'stopped':
            show_download_information = (str(round(converted_downloaded_size, 2))
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
                                          show_download_information))
            sys.stdout.write('\x1b[2K')
            sys.stdout.write('  Please wait...\n')
            sys.stdout.flush()

        elif self.download_status == 'error':
            show_download_information = (str(round(converted_downloaded_size, 2))
                                         + '|' + str(size)
                                         + ' ' + unit)
            # cursor up one line
            sys.stdout.write('\x1b[1A')
            # delete last line
            sys.stdout.write('\x1b[2K')
            sys.stdout.write(
                '[%s] %s%s ...%s   \n' % ('Error!',
                                          int(percent),
                                          '%',
                                          show_download_information))
            sys.stdout.write('\x1b[2K')
            sys.stdout.write('  Please wait...\n')
            sys.stdout.flush()

    # this method runs progress bar and speed calculator
    def runProgressBar(self):
        # run  a thread for calculating download speed.
        calculate_speed_thread = threading.Thread(
            target=self.downloadSpeed)
        calculate_speed_thread.setDaemon(True)
        calculate_speed_thread.start()

        # add thus thread to thread_list
        self.thread_list.append(calculate_speed_thread)

        if self.progress_bar is True:
            # run a thread for showing progress bar
            progress_bar_thread = threading.Thread(
                target=self.progressBar)
            progress_bar_thread.setDaemon(True)
            progress_bar_thread.start()

        # add thus thread to thread_list
        self.thread_list.append(progress_bar_thread)

    # threadHandler asks new part for download from this method.
    def askForNewPart(self):
        self.lock = True
        for i in range(0, self.number_of_parts):
            # Check that this part is not being downloaded or its download is not complete.
            # Check that the number of retries of this part has not reached the set limit.
            if (self.download_infromation_list[i][2] not in ['complete', 'downloading']) and (self.download_infromation_list[i][3] != self.retry):
                # set 'downloding' status for this part
                self.download_infromation_list[i][2] = 'downloading'
                # add 1 to retry number for this part
                self.download_infromation_list[i][3] += 1
                break

            # no part found
            if i == self.number_of_parts:
                i = None

        self.lock = False
        return i

    # The below code is used for each chunk of file handled
    # by each thread for downloading the content from specified
    # location to storage
    def threadHandler(self, thread_number):
        while self.download_status in ['downloading', 'paused']:

            # Wait for the lock to be released.
            while self.lock is True:
                # Random sleep prevents two threads from downloading the same part at the same time.
                # sleep random time
                time.sleep(random.uniform(0, 0.5))
            part_number = self.askForNewPart()

            # If part_number is None, no part is available for download. So exit the loop.
            if part_number is None:
                break

            self.part_thread_dict[part_number] = thread_number

            try:
                # calculate part size
                if part_number != (self.number_of_parts - 1):
                    part_size = self.download_infromation_list[part_number + 1][0] - self.download_infromation_list[part_number][0]
                else:
                    part_size = self.file_size - self.download_infromation_list[part_number][0]

                # get start byte number of this part and add it to downloaded size. download resume from this byte number
                downloaded_part = self.download_infromation_list[part_number][1]
                start = self.download_infromation_list[part_number][0] + downloaded_part

                # end of part is equal to start of the next part
                if part_number != (self.number_of_parts - 1):
                    end = self.download_infromation_list[part_number + 1][0]
                else:
                    end = self.file_size

                # specify the start and end of the part for request header.
                chunk_headers = {'Range': 'bytes=%d-%d' % (start, end)}

                # request the specified part and get into variable
                self.requests_session.headers.update(chunk_headers)
                response = self.requests_session.get(
                    self.link, allow_redirects=True, stream=True,
                    timeout=self.timeout)

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
                    # so we divide our chunk to smaller chunks. default is 100 KiB
                    python_request_chunk_size = (1024
                                                 * self.python_request_chunk_size)
                    for data in response.iter_content(
                            chunk_size=python_request_chunk_size):
                        if self.download_status in ['downloading', 'paused']:

                            fp.write(data)

                            # if this part is download by another thread then exit thread
                            if self.part_thread_dict[part_number] != thread_number:
                                # This loop does not end due to an error in the request.
                                # Therefore, no number should be added to the number of retries.
                                self.download_infromation_list[part_number][3] -= 1
                                break

                            # maybe the last chunk is less than default chunk size
                            if (part_size - downloaded_part) >= python_request_chunk_size:
                                update_size = python_request_chunk_size
                                # if update_size is not equal with actual data length,
                                # then redownload this chunk.
                                # exit this "for loop" for redownloading this chunk.
                                if update_size != len(data):
                                    # This loop does not end due to an error in the request.
                                    # Therefore, no number should be added to the number of retries.
                                    self.download_infromation_list[part_number][3] -= 1
                                    break

                            else:
                                # so the last small chunk is equal to :
                                update_size = (part_size - downloaded_part)
                                # so the last small chunk is equal to :
                                update_size = (part_size - downloaded_part)
                                # some times last chunks are smaller
                                if len(data) < update_size:
                                    update_size = len(data)

                            # if update_size is not equal with actual data length,
                            # then redownload this chunk.
                            # exit this "for loop" for redownloading this chunk.
                            if update_size != len(data):
                                # This loop does not end due to an error in the request.
                                # Therefore, no number should be added to the number of retries.
                                self.download_infromation_list[part_number][3] -= 1
                                break

                            # update downloaded_part
                            downloaded_part = (downloaded_part
                                               + update_size)
                            # save value to downloaded_size_list
                            self.download_infromation_list[part_number][1] = downloaded_part

                            # this variable saves amount of total downloaded size
                            # update downloaded_size
                            self.downloaded_size = (self.downloaded_size
                                                    + update_size)
                            # perhaps user set limitation for download rate.
                            # downloadrate limitation
                            # "Speed limit" is whole number. The more it is, the more sleep time is given to the data
                            # receiving loop, which reduces the download speed.
                            time.sleep(self.sleep_for_speed_limiting)

                            if self.download_status == 'paused':
                                # wait for unpausing
                                while self.download_status == 'paused':
                                    time.sleep(0.2)
                        else:
                            self.download_infromation_list[part_number][2] = 'stopped'
                            break

            except Exception as e:
                self.download_infromation_list[part_number][2] = 'error'
                error_text = ("part_number: "
                              + str(part_number)
                              + " " + str(e))
                sendToLog(error_text)

            # so it's complete successfully.
            if (downloaded_part == part_size):
                sendToLog('part ' + str(part_number) + ' is complete!')
                self.download_infromation_list[part_number][2] = 'complete'
                self.part_thread_dict[part_number] = None
            else:
                self.download_infromation_list[part_number][2] = 'error'
                self.part_thread_dict[part_number] = None

        # This thread is finished.
        self.finished_threads = self.finished_threads + 1

    # this method save download information in json format every 1 second
    def saveInfo(self):
        while self.download_status == 'downloading' or self.download_status == 'paused':
            control_dict = {
                'ETag': self.etag,
                'file_name': self.file_name,
                'file_size': self.file_size,
                'number_of_parts': self.number_of_parts,
                'download_infromation_list': self.download_infromation_list}

            # write control_dict in json file
            with open(self.control_json_file_path, "w") as outfile:
                json.dump(control_dict, outfile, indent=2)

            time.sleep(1)

    # this method runs download threads
    def runDownloadThreads(self):

        # check if server supports multithread downloading or not!
        if self.multiThreadSupport() is False:
            self.thread_number = 1

        for i in range(0, self.number_of_threads):

            # sleep between starting new thread.
            # it solves "Connection refused" error.
            time.sleep(0.1)

            # create threads
            t = threading.Thread(
                target=self.threadHandler,
                kwargs={'thread_number': i})
            t.setDaemon(True)
            t.start()

            # add this thread to thread_list
            self.thread_list.append(t)

        # run saveInfo thread for updating control file
        save_control_thread = threading.Thread(
            target=self.saveInfo)
        save_control_thread.setDaemon(True)
        save_control_thread.start()

        # add this thread to thread_list
        self.thread_list.append(save_control_thread)

    # this method checks and manages download progress.
    def checkDownloadProgress(self):
        # Run this loop until the download is finished.
        while (self.file_size != self.downloaded_size) and (self.download_status == 'downloading' or self.download_status == 'paused') and \
              (self.finished_threads != self.number_of_threads):

            # Calculate download percent
            self.download_percent = int((self.downloaded_size / self.file_size) * 100)

            # Calculate number of active threads
            self.number_of_active_connections = self.number_of_threads - self.finished_threads
            time.sleep(1)

        # Calculate download percent
        self.download_percent = int((self.downloaded_size / self.file_size) * 100)

        sendToLog(str(self.finished_threads))
        # If the downloaded size is the same as the file size, then the download has been completed successfully.
        if self.file_size == self.downloaded_size:

            self.download_status = 'complete'
            sendToLog('Download complete.')

        # If the download is not complete and the user has not stopped the download, then the download has encountered an error.
        elif self.download_status != 'stopped':

            self.download_status = 'error'
            sendToLog('Error')

        elif self.download_status == 'stopped':

            sendToLog('Download stopped.')

        print('\r', flush=True)

    # this method starts download
    def start(self):
        self.createSession()
        file_size = self.getFileSize()
        if file_size:
            self.setRetry()
            self.download_status = 'downloading'
            self.getFileName()

            self.getFileTag()

            self.createControlFile()
            self.definePartSizes()

            self.runProgressBar()

            self.runDownloadThreads()

            self.checkDownloadProgress()
        else:
            self.download_status = 'error'
        self.close()

    def stop(self, signum, frame):
        self.download_status = 'stopped'

    def downloadPause(self):
        self.download_status = 'paused'

    def downloadUnpause(self):
        self.download_status = 'downloading'

    # This method returns download status
    def tellStatus(self):
        downloded_size, downloaded_size_unit = humanReadableSize(self.downloaded_size)
        file_size, file_size_unit = humanReadableSize(self.file_size)

        # return information in dictionary format
        download_info = {
            'file_name': self.file_name,
            'status': self.download_status,
            'size': str(file_size) + ' ' + file_size_unit,
            'downloaded_size': str(downloded_size) + ' ' + downloaded_size_unit,
            'percent': str(self.download_percent) + '%',
            'connections': str(self.number_of_active_connections),
            'rate': self.download_speed_str,
            'estimate_time_left': self.eta,
            'link': self.link
        }

        return download_info

    # This method limits download speed.
    # limit_value is between 1 to 10.
    # 10 means no limit speed.
    def limitSpeed(self, limit_value):
        # Calculate sleep time between data receiving. It's reduce download speed.
        self.sleep_for_speed_limiting = (10 - limit_value) * 0.005 * (self.number_of_active_connections)

    def close(self):
        # if download complete, so delete control file
        if self.download_status == 'complete':
            os.remove(self.control_json_file_path)

        # delete last line
        if self.progress_bar is True:
            sys.stdout.write('\x1b[2K')
            sys.stdout.write('  persepolis_lib is closed!\n')
            sys.stdout.flush()

        # close requests session
        self.requests_session.close()

        # ask threads for exiting.
        for thread in self.thread_list:
            thread.join()

        sendToLog("persepolis_lib is closed!")
