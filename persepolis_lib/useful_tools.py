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

from pathlib import Path
import urllib.parse
import logging
import os
import requests
# define logging object
logObj = logging.getLogger("Persepolis")
logObj.setLevel(logging.INFO)

# don't show log in console
logObj.propagate = False

log_file = os.path.join(os.path.expanduser('~'), 'persepolis_lib_log.log')

# create a file handler
handler = logging.FileHandler(log_file)
handler.setLevel(logging.INFO)
# create a logging format
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logObj.addHandler(handler)


def sendToLog(text="", type="INFO"):
    if type == "INFO":
        logObj.info(text)
    elif type == "ERROR":
        logObj.error(text)
    else:
        logObj.warning(text)

# this function converts second to hour and minute


def convertTime(time):
    minutes = int(time // 60)
    if minutes == 0:
        return str(int(time)) + 's'
    elif minutes < 60:
        return str(minutes) + 'm'
    else:
        hours = minutes // 60
        minutes = minutes - (hours * 60)
        return str(hours) + 'h ' + str(minutes) + 'm'


# this function converts file_size to KiB or MiB or GiB
def humanReadableSize(size, input_type='file_size'):
    labels = ['KiB', 'MiB', 'GiB', 'TiB']
    i = -1
    if size < 1024:
        return size, 'B'

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

    return round(converted_size, 2)


# this method get http header as string and convert it to dictionary
def convertHeaderToDictionary(headers):
    dic = {}
    for line in headers.split("\n"):
        if line.startswith(("GET", "POST")):
            continue
        point_index = line.find(":")
        dic[line[:point_index].strip()] = line[point_index + 1:].strip()
    return dic


def readCookieJar(load_cookies):
    jar = None
    if os.path.isfile(load_cookies):
        # Open cookie file
        cookies_txt = open(load_cookies, 'r')

        # Initialize RequestsCookieJar
        jar = requests.cookies.RequestsCookieJar()

        for line in cookies_txt.readlines():
            words = line.split()

            # Filter out lines that don't contain cookies
            if (len(words) == 7) and (words[0] != "#"):
                # Split cookies into the appropriate parameters
                jar.set(words[5], words[6], domain=words[0], path=words[2])

        return jar


# get file name from link string.
def getFileNameFromLink(link):
    link = requests.utils.unquote(link)
    parsed_linkd = urllib.parse.urlparse(link)
    file_name = Path(parsed_linkd.path).name

    return file_name
