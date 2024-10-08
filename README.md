# persepolis_lib

### **About**
A Python library for easier and faster downloading

### **Features**
- Multi-segment downloading(64 connections)
- Resuming downloads 

## Installation
persepolis_lib is available on [pypi](https://pypi.org/project/persepolis-lib/).
```
pip install persepolis-lib
```
## Usage
```python
#!/usr/bin/python3

# import Download class
from persepolis_lib.persepolis_lib import Download

# create a dictionary that contains download infromation.
download_dict = {'link': http://example.com/example.jpg, # your download link
                       'out': None, # You can choose a name for your file if you want. If you don't want to, choose None for its value.
                       'download_path': /home/example_user/Downloads, # Choose download path. You must choose valid download path!
                       'ip': None, # set ip of your proxy, If you don't use proxy, set None value for it.
                       'port': None, # set port of your proxy, If you don't use proxy, set None value for it.
                       'proxy_user': None, # set proxy user, If you don't use proxy, set None value for it.
                       'proxy_passwd': None, # set proxy pass word, If you don't use proxy, set None value for it.
                       'proxy_type': None, # set proxy type, http or socks5. If you don't use proxy, set None value for it.
                       'download_user': None, # set username, If your download link requires user name,Otherwise, set its value to ٔNone.
                       'download_passwd': None, # set password, If your download link requires user name and password,Otherwise, set its value to ٔNone.
                       'header': None, # set header if you want, Otherwise, set its value to ٔNone.
                       'user_agent': None, # set user-agent if you want, Otherwise, set its value to ٔNone. persepolis_lib/version is default user agent.
                       'load_cookies': None, # set cookies path if you want, Otherwise, set its value to ٔNone.
                       'referer': None} # set referrer if you want, Otherwise, set its value to ٔNone.
# persepolis supports Multi-segment downloading. set number of threads. maximum value is 64. minimum value is 1. default is 64.
segments = 64

# set python requests chunk size in KiB.
# checkout this link for more informaton. https://stackoverflow.com/questions/46205586/why-to-use-iter-content-and-chunk-size-in-python-requests
# default is 100 KiB
pytho_requests_chunk_size = 100 # KiB

# create a download session
# set timeout value in seconds. default is 5.
# set number of retries if download failed. default is 5.
# set progress_bar value to True If you want the progress bar to be shown in the console. default is False
# set threads_progress_bar to True If you want the size downloaded by each thread to be displayed in the progress bar. default is False.
download_session = Download(add_link_dictionary=download_dict, number_of_threads=segments,
                             chunk_size=pytho_requests_chunk_size, timeout=5, retry=5, progress_bar=False, threads_progress_bar=False)
# start download. Use thread if you want!
download_session.start()

# stop download
download_session.stop()

# pause download
download_session.downloadPause()

# Unpause
download_session.downloadUnPause()

# limit download speed.
# limit_value is between 1 to 10.
# 10 means no limit speed.
download_session.limitSpeed(5)

# get download information in dictionary format
status_dict = download_session.tellStatus()
print(status_dict)

```

persepolis_lib creates download file and log file and conrol file in json format with .persepolis extension in download path. control file contains download information.
Persepolis_lib can resume download, If control file exists.
