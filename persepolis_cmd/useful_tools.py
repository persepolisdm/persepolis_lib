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


def convertTime(time):
    minutes = int(time // 60)
    if minutes == 0:
        return str(int(time)) + ' s'
    elif minutes < 60:
        return str(minutes) + ' m'
    else:
        hours = minutes // 60
        minutes = minutes - (hours * 60)
        return str(hours) + ' h' + str(minutes) + ' m'


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