import re
import os
import ast
import shlex
import types
import logging
import subprocess
import youtube_dl

from youtube_dl.downloader.common import FileDownloader
from urllib.parse import urlparse, parse_qs, unquote
from requests_html import HTMLSession
from selenium import webdriver


def create_logger():

    # Create subclasses
    class _Formatter(logging.Formatter):
        def format(self, record):
            record.levelname = record.levelname.lower()
            return super(_Formatter, self).format(record)

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(_Formatter(fmt='[%(levelname)s] %(message)s'))

    # Create an empty format handler for youtube_dl and other stuff
    no_fmt_handler = logging.StreamHandler()
    no_fmt_handler.setLevel(logging.DEBUG)
    no_fmt_handler.setFormatter(_Formatter(fmt='%(message)s'))

    # Create a "blank line" handler
    blank_handler = logging.StreamHandler()
    blank_handler.setLevel(logging.DEBUG)
    blank_handler.setFormatter(_Formatter(fmt=''))

    # Create a log file for all of it
    file_handler = logging.FileHandler('log', 'w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_Formatter('[%(levelname)s] %(message)s'))

    # Create a logger, with the previously-defined handler
    logger = logging.getLogger('du_downloader')
    logger.setLevel(logging.DEBUG)

    # Create an empty format logger for youtube_dl and other stuff
    logger.no_fmt = logging.getLogger('no_format')
    logger.no_fmt.setLevel(logging.DEBUG)

    # Add relevant handlers to all the loggers
    logger.addHandler(console_handler)
    logger.no_fmt.addHandler(no_fmt_handler)
    [x.addHandler(file_handler) for x in (logger, logger.no_fmt)]

    # Create newline method
    def log_newline(self, newlines=1):
        # Switch handler, output blank line(s)
        self.removeHandler(self.console_handler)
        self.addHandler(self.blank_handler)
        for i in range(newlines):
            self.info('')
        # Switch back
        self.removeHandler(self.blank_handler)
        self.addHandler(self.console_handler)

    # Save some data and add a method to logger object
    logger.console_handler = console_handler
    logger.blank_handler = blank_handler
    logger.no_fmt.file_handler = file_handler
    logger.newline = types.MethodType(log_newline, logger)

    return logger

class Downloader:
    def __init__(self):

        self.logger = create_logger()

        self.url = 'https://learn.du.se/ultra/'
        self.session = HTMLSession()

        if os.path.isfile('cookies'):
            with open('cookies', 'r') as f:
                self.cookies = ast.literal_eval(f.read())
                for cookie in self.cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])
        else:
            self.get_cookies()

    def get_cookies(self):
        self.logger.info('Running login process using selenium (chrome driver)...')
        browser = webdriver.Chrome()

        browser.get(self.url)
        browser.find_element_by_id('username').send_keys('iwconfig')
        browser.find_element_by_id('password').send_keys('plz hack me')
        browser.find_element_by_class_name('btn-submit').click()

        self.logger.info('Saving cookies...')

        self.cookies = browser.get_cookies()
        self.session.cookies.clear()

        for cookie in self.cookies:
            self.session.cookies.set(cookie['name'], cookie['value'])

        with open('cookies', 'w') as f:
            f.write(str(self.cookies))

        browser.close()

    def _response(self, url):
        count = 1
        while True:
            response = self.session.get(url, stream=True)
            if response.ok:
                self.logger.info('Connected to: %s', url)
                return response
            else:
                self.logger.info('Status code: %s', response.status_code)
                if response.status_code == 401:
                    self.get_cookies()
                if count >= 3:
                    self.logger.error('Could not connect to %s', url)
                    return None
                self.logger.error('Connection error: trying again... #%i', count)
                count += 1

    def get(self, url):
            return self._response(url)

    def dl_file(self, url, path):
        resp = self.get(url)
        os.makedirs(path, exist_ok=True)
        url = resp.url
        query = urlparse(url).query
        file_name = unquote(os.path.basename(parse_qs(query)['response-content-disposition'][0].split("''")[-1]))
        path = os.path.join(path, file_name)
        self.logger.info('-: INITIALIZING FILE DOWNLOAD :-')
        self.logger.info('Filename: %s', file_name)
        if os.path.exists(path):
            if os.path.getsize(path) == int(resp.headers['Content-length']):
                self.logger.info('File already exists! Skipping...')
                return

        with open(path, 'wb') as f:
            self.logger.info('Writing to local file...')
            f.write(resp.content)
        self.logging.info('Done!')

    def _youtube_dl(self, url, path):
        def _logger(self, message, skip_eol=False):
            self.params['logger'].info(message)

        def logger_progress_hook(fn):
            def _logger_progress_hook(self, *args, **kwargs):
                status = args[0]['status']
                if status in ('finished', 'error'):
                    self.ydl.params['logger'].handlers[0].terminator = '\n'
                    #self.ydl.params['logger'].file_handler.terminator = '\n'
                elif status == 'downloading':
                    self.ydl.params['logger'].handlers[0].terminator = ''
                    #self.ydl.params['logger'].file_handler.terminator = ''
                fn(self, *args, **kwargs)
            return _logger_progress_hook

        youtube_dl.YoutubeDL.to_screen = _logger
        FileDownloader.report_progress = logger_progress_hook(FileDownloader.report_progress)

        path += '.%(ext)s'
        ydl_opts = {
            'outtmpl': path,
            'merge_output_format': 'mp4',
            'fixup': 'warn',
            #'download_archive': '/tmp/du-downloader-ytdl',
            'external_downloader_args': ['quiet', True, 'continuedl', True],
            'hls_prefer_native': True,
            'consoletitle': True,
            'logger': self.logger,
            'verbose': False
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            self.logger.info('Handing over video url to youtube-dl for download')
            ydl.download([url])

        #cmd = 'youtube-dl {0} -o "{1}"'.format(url, path)
        #self.logger.info('Running command: %s', cmd)
        #subprocess.check_output(shlex.split(cmd))

    def dl_video(self, url, path):
        resp = self.get(url)
        for element in resp.html.find('.item'):
            a = element.find('a')[0]
            title = a.text
            url = next(iter(a.links))

            if url.startswith('/bbcswebdav/'):
                url = 'https://learn.du.se' + url
                self.dl_file(url, path)
                continue

            self.logger.info('-: INITIALIZING VIDEO DOWNLOAD :-')
            if url.startswith('mms://'):
                self._youtube_dl(url, os.path.join(path, title))
                continue

            resp = self.get(url)
            regex = 'playlist(High|Low)\.push\((.*?)\);'
            match = list(map(lambda x: (x[0], ast.literal_eval(x[1])), re.findall(regex, resp.text)))
            if len(match) == 0:
                regex = 'playlist\s\=\s\[(.*?)\];'
                match = ast.literal_eval(re.findall(regex, resp.html.text)[0].strip())
                if len(match) == 0:
                    self.logger.error('Could not find video!')
                for x in match['sources']:
                    if x['file'].endswith('.m3u8'):
                        url = x['file']
                        if match['title']:
                            _title = '{} - {}'.format(title, match['title'])
                        else:
                            _title = title
                        self._youtube_dl(url, os.path.join(path, _title))
                        continue
                continue

            parts = set()

            high = [x if x[0] == 'High' else None for x in match]
            low = [x if x[0] == 'Low' else None for x in match]

            for h,l in zip(high, low):
                q = h or l
                if q[1]['title'] in parts:
                    continue
                if q[1]['title']:
                    _title = '{} - {}'.format(title, q[1]['title'])
                else:
                    _title = title
                url = q[1]['sources'][0]['file']
                self.logger.info('Title: %s', _title)
                self.logger.info('Quality: %s', q[0])
                self._youtube_dl(url, os.path.join(path, _title))
                parts.add(q[1]['title'])
                continue

with open('data', 'r') as f:
    data = ast.literal_eval(f.read())

session = Downloader()
for kurs,v in data.items():
    for name,url in v['moment'].items():
        if isinstance(url, dict):
            for NAME,URL in url.items():
                path = '/home/d/Hämtningar/learn.du.se/{}/'.format(kurs)
                #path = '/tmp/'
                session.dl_file(URL, path)
                session.logger.newline()
                session.logger.no_fmt.info('-'*50)
                session.logger.newline()
        else:
            path = '/home/d/Hämtningar/learn.du.se/{}/{}'.format(kurs, name)
            #path = '/tmp/'
            session.dl_video(url, path)
            session.logger.newline()
            session.logger.no_fmt.info('-'*50)
            session.logger.newline()

#************#
#*-Junkyard-*#
#************#

            # if d['status'] == 'downloading':
                # barLength, status = 20, ""
                # progress = float(d['fragment_index']) / float(d['fragment_count'])
                # if progress >= 1.:
                #     progress, status = 1, "\r\n"
                # block = int(round(barLength * progress))

                # def ETA(_):
                #     h, m, s = _//3600, _%3600//60, _%60

                #     if h != 0:
                #         return '{:2}h {:2}m {:2}s'.format(h,m,s)
                #     elif m != 0:
                #         return '{:2}m {:2}s'.format(m,s)
                #     else:
                #         return '{:2}s'.format(s)

                # def speed(s):
                #     if s:
                #         if int(s) == 0:
                #             return '{:.2f}KiB'.format(s/float(1<<10))
                #         return '{:.2f}MiB'.format(s/float(1<<20))

                # text = "\r[{}] {:.0f}% | Speed: {} | ETA: {} {}".format(
                #     "#" * block + "-" * (barLength - block),
                #     round(progress * 100, 0),
                #     speed(d['speed']),
                #     ETA(d['eta']),
                #     status)
                # print(text, end='')
