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
from persepolis_lib import Download
import sys

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
parser.add_argument('--download-user', action='store', nargs=1,
                    help='Download user name')
parser.add_argument('--download-password', action='store', nargs=1,
                    help='Download pass word')
parser.add_argument('--header', action='store', nargs=1,
                    help='Append HEADER to HTTP request header.')
parser.add_argument('--user-agent', action='store', nargs=1,
                    help='Set user agent for HTTP(S) downloads.')
parser.add_argument('--cookie', action='store', nargs=1, help='Cookie')
parser.add_argument('--referrer', action='store', nargs=1,
                    help='Set an http referrer')
args, unknownargs = parser.parse_known_args()

add_link_dictionary = {'link': None,
                       'out': None,
                       'download_path': None,
                       'ip': None,
                       'port': None,
                       'proxy_user': None,
                       'proxy_passwd': None,
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

if __name__ == '__main__':
    download_item = Download(add_link_dictionary, number_of_threads)
    signal.signal(signal.SIGINT, download_item.stop)
    download_item.createSession()
    file_size, headers = download_item.getFileSize()
    if file_size:
        download_item.getFileName(headers)

        part_size = download_item.createFile()

        download_item.runProgressBar()

        download_item.runDownloadThreads(part_size)
    # delete last line
    sys.stdout.write('\x1b[2K')
    sys.stdout.write('  Persepolis CMD is closed!\n')
    sys.stdout.flush()
