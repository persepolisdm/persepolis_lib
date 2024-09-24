#!/usr/bin/env python3
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

import signal
import argparse
import sys
import os
import platform

# finding os platform
os_type = platform.system()

# Don't run persepolis as root!
if os_type == 'Linux' or os_type == 'FreeBSD' or os_type == 'OpenBSD' or os_type == 'Darwin':
    uid = os.getuid()
    if uid == 0:
        print('Do not run persepolis_lib as root.')
        sys.exit(1)


cwd = os.path.abspath(__file__)
run_dir = os.path.dirname(cwd)
# if persepolis run in test folder
print('persepolis_lib is running from test folder')
parent_dir = os.path.dirname(run_dir)

sys.path.insert(0, parent_dir)

from persepolis_lib.persepolis_lib import Download

# create  terminal arguments
parser = argparse.ArgumentParser(
    description='Persepolis command line download utility')
parser.add_argument('--version',
                    action='version', version='Persepolis CMD 0.0.1')
parser.add_argument('--link',
                    action='store', nargs=1,
                    help='Download link.(Use "" for links)')
parser.add_argument('--name',
                    action='store', nargs=1,
                    help='The  file  name  of  the downloaded file\
                            with extension.')
parser.add_argument('--number-of-threads',
                    action='store', nargs=1, help='Number of threads.')
parser.add_argument('--download-path', action='store', nargs=1,
                    help='Set download path.')
parser.add_argument('--proxy-ip', action='store', nargs=1, help='Proxy IP')
parser.add_argument('--proxy-port', action='store', nargs=1, help='proxy port')
parser.add_argument('--proxy-user',
                    action='store', nargs=1, help='Proxy user name')
parser.add_argument('--proxy-password', action='store', nargs=1,
                    help='Proxy pass word')
parser.add_argument('--proxy-type', action='store', nargs=1,
                    help='set type proxy. http or socks5')
parser.add_argument('--download-user', action='store', nargs=1,
                    help='Download user name')
parser.add_argument('--download-password', action='store', nargs=1,
                    help='Download pass word')
parser.add_argument('--header', action='store', nargs=1,
                    help='Append HEADER to HTTP request header.')
parser.add_argument('--user-agent', action='store', nargs=1,
                    help='Set user agent for HTTP(S) downloads.')
parser.add_argument('--cookie', action='store', nargs=1, help='Cookies file path')
parser.add_argument('--referrer', action='store', nargs=1,
                    help='Set an http referrer')
parser.add_argument('--chunk-size', action='store', nargs=1,
                    help='Chunk size in KiB, Default is 200 KiB')
args, unknownargs = parser.parse_known_args()

add_link_dictionary = {'link': None,
                       'out': None,
                       'download_path': None,
                       'ip': None,
                       'port': None,
                       'proxy_user': None,
                       'proxy_passwd': None,
                       'proxy_type': None,
                       'download_user': None,
                       'download_passwd': None,
                       'header': None,
                       'user_agent': None,
                       'load_cookies': None,
                       'referer': None}


if args.link:
    add_link_dictionary['link'] = "".join(args.link)

if args.name:
    add_link_dictionary['out'] = "".join(args.name)

if args.download_path:
    add_link_dictionary['download_path'] = "".join(args.download_path)

if args.proxy_ip:
    add_link_dictionary['ip'] = "".join(args.proxy_ip)

if args.proxy_port:
    add_link_dictionary['port'] = "".join(args.proxy_port)

if args.proxy_user:
    add_link_dictionary['proxy_user'] = "".join(args.proxy_user)

if args.proxy_password:
    add_link_dictionary['proxy_passwd'] = "".join(args.proxy_password)

if args.proxy_type:
    add_link_dictionary['proxy_type'] = "".join(args.proxy_type)

if args.download_user:
    add_link_dictionary['download_user'] = "".join(args.download_user)

if args.download_password:
    add_link_dictionary['download_passwd'] = "".join(args.download_password)

if args.header:
    add_link_dictionary['header'] = "".join(args.header)


if args.user_agent:
    add_link_dictionary['user_agent'] = "".join(args.user_agent)

if args.cookie:
    add_link_dictionary['load_cookies'] = "".join(args.cookie)

if args.referrer:
    add_link_dictionary['referer'] = "".join(args.referrer)

if args.number_of_threads:
    number_of_threads = "".join(args.number_of_threads)
else:
    number_of_threads = 4

if args.chunk_size:
    chunk_size = "".join(args.chunk_size)
else:
    chunk_size = 200


if __name__ == '__main__':
    # create download object
    download_item = Download(add_link_dictionary, int(number_of_threads),
                             int(chunk_size), progress_bar=True, threads_progress_bar=False)

    # capture SIGINT signal
    signal.signal(signal.SIGINT, download_item.stop)

    # start download
    download_item.start()
