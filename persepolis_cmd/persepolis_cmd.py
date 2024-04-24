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

import argparse
from persepolis_lib import downloadFile

# create  terminal arguments
parser = argparse.ArgumentParser(description='Persepolis command line download utility')
parser.add_argument('--version', action='version', version='Persepolis CMD 1.0.0')
parser.add_argument('--link', action='store', nargs=1, help='Download link.(Use "" for links)')
parser.add_argument('--name', action='store', nargs=1, help='The  file  name  of  the downloaded file with extension. ')
parser.add_argument('--number-of-threads', action='store', nargs=1, help='Number of threads.')
parser.add_argument('--download-path', action='store', nargs=1, help='Number of threads.')



args, unknownargs = parser.parse_known_args()

add_link_dictionary = {}


if args.link:
    add_link_dictionary['link'] = "".join(args.link)


if args.name:
    add_link_dictionary['out'] = "".join(args.name)
else:
    add_link_dictionary['out'] = None

if args.download_path:
    add_link_dictionary['download_path'] = "".join(args.download_path)
else:
    add_link_dictionary['download_path'] = None

if args.number_of_threads:
    number_of_threads = "".join(args.number_of_threads)
else:
    number_of_threads = 4

if __name__ == '__main__': 
    downloadFile(add_link_dictionary, number_of_threads)
