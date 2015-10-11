import os
import re
import sys
import json
import string
import platform
import subprocess
import urllib.request

import wgetter
import mutagen
from mutagen.mp3 import MP3
from mutagen.id3 import APIC
from mutagen.easyid3 import EasyID3


class BandLoader(object):

    def __init__(self, url, directory):
        self.__url = url
        self.__directory = directory
        # Full file path of our folder
        self.__file_path = ""
        # This is the sorted data from the webpage
        self.__album_data = {}

    @property
    def album_data(self):
        """
        getter for __albun_data

        :return __album_data:
        """
        return self.__album_data

    @property
    def file_path(self):
        """
        getter for file_path

        :return file_path:
        """
        return self.__file_path


    @staticmethod
    def get_html_data(query, source, brackets=False):
        """
        Scrapes Bandcamp site for query

        :param query:
        :param source:
        :param brackets:
        :return:
        """
        try:
            if brackets:
                return json.loads("[{" + (re.findall(query + "[ ]?: \[?\{(.+)\}\]?,", source, re.MULTILINE)[0] + "}]"))
            return re.findall(query + "[ ]?: ([^,]+)", source, re.DOTALL)[0]
        except:
            print("Unable to load site and get source")
            sys.exit(0)

    @staticmethod
    def fix_release_date(date_list):
        """
        Deletes the hour and time from date
        we got from website, just for encoding

        :param date_list:
        :return:
        """
        date_list = date_list.split(" ")
        new_date_list = []
        for i in range(3):
            new_date_list.append(date_list[i])
        return new_date_list

    def create_dir(self):
        """
        Create the directory for saving the downloaded files

        """
        file_path = self.__directory + "\\" + self.__album_data['title'] + "\\"

        if not os.path.exists(file_path):
            os.makedirs(file_path)
        else:
            os.path.expanduser(file_path)

        self.__file_path = file_path

    def collect_album_info(self):
        """
        Collects information by crawling through the website
        stores information into album_data dictionary and then
        returns information

        """
        i = 0
        no_links = []
        tmp_site = urllib.request.urlopen(self.__url)
        site_source = tmp_site.read().decode('utf-8')
        tmp_site.close()
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        self.__album_data['track_info'] = self.get_html_data('trackinfo', site_source, True)
        self.get_track_titles()
        num_of_tracks = len(self.__album_data['track_titles'])

        # Checks the list of tracks for links, if we dont find the links remove them
        # Replace title with a empty string
        for track in self.__album_data['track_titles']:
            if not self.__album_data['track_info'][i]['file']:
                no_links.append(track)
                self.__album_data['track_titles'][i] = ''
            i += 1
        # Remove links for tracks that dont have download links
        while num_of_tracks > 0:
            if not self.__album_data['track_info'][num_of_tracks - 1]['file']:
                self.__album_data['track_info'].pop(num_of_tracks - 1)
            num_of_tracks -= 1

        # Delete empty strings, helps with download time and errors when downloading
        while '' in self.__album_data['track_titles']:
            self.__album_data['track_titles'].remove('')

        self.__album_data['artist'] = self.get_html_data("artist", site_source).replace('"', '')
        self.__album_data['artist'] = ''.join(c for c in self.__album_data['artist'] if c in valid_chars)
        self.__album_data['title'] = self.get_html_data("album_title", site_source).replace('"', '')
        self.__album_data['title'] = ''.join(c for c in self.__album_data['title'] if c in valid_chars)
        self.__album_data['release_date'] = self.get_html_data("release_date", site_source).replace('"', '')
        self.__album_data['cover_url'] = self.get_html_data("artFullsizeUrl", site_source).replace('"', '')
        self.__album_data['release_date'] = self.fix_release_date(self.__album_data['release_date'])
        self.__album_data['invalid_tracks'] = no_links

    def get_track_titles(self):
        """
        Gets the track titles from

        Also fixes the track titles and removes any invalid file names that it may have

        For example chars such as *, /, ?
        are removed from the name, so that when it saves the mp3
        file we don't get an error

        """
        self.__album_data['track_titles'] = []
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        for track in self.__album_data['track_info']:
            valid_track_name = track['title']
            track['title'] = ''.join(c for c in valid_track_name if c in valid_chars)
            self.__album_data['track_titles'].append(track['title'])

    @staticmethod
    def download_tracks(track_info, track_title, directory):
        """
        Downloads the track that was sent to it
        Skips over tracks that have already been downloaded

        :param track_info:
        :param track_title:
        :param directory:
        :return:
        """
        download_url = track_info['file']['mp3-128']
        # downloads the mp3 from url, creates
        # a temporary file in the directory
        tmp_file = wgetter.download(download_url, outdir=directory)
        # create the file name with path and .mp3
        file_name = directory + "\\" + track_title + ".mp3"
        # if file already exists, we skip that file and delete the tmp_file
        if os.path.isfile(file_name):
            print("Skipping file: " + file_name + " already exists.")
            pass
        else:
            # replace the name of tmp_file with
            # track title and .mp3
            os.rename(tmp_file, file_name)
            print("\nDone downloading track\n")

    def download_album_cover(self):
        """
        Downloads album cover from URL

        """
        print("\nDownloading album cover...\n")
        tmp_file = wgetter.download(self.__album_data['cover_url'], outdir=self.__file_path)
        self.__album_data['cover'] = self.__file_path+ "\\" + "cover.jpg"
        # if file already exists, we skip that file and delete the tmp_file
        if os.path.isfile(self.__album_data['cover']):
            os.remove(tmp_file)
            print("Skipping file: " + self.__album_data['cover_url'] + " already exists.")
        else:
            os.rename(tmp_file, self.__album_data['cover'])
            print("\nDone downloading album cover!\n")

    def encode_tracks(self):
        """
        Using mutagen this encodes the .MP3
        files so that iTunes and other
        players can know what Artist,
        album, etc are.

        """
        print("Encoding...")
        i = 0
        for track in self.__album_data['track_titles']:
            file_name = self.__file_path + track + ".mp3"
            try:
                file_to_encode = EasyID3(file_name)
            except mutagen.id3.ID3NoHeaderError:
                print("\nFile didnt have ID3 tag, tagging now\n")
                file_to_encode = mutagen.File(file_name, easy=True)
                file_to_encode.add_tags()
            # add the mp3 tags to the audio files
            file_to_encode['tracknumber'] = str(i + 1)
            file_to_encode['title'] = track
            file_to_encode['artist'] = self.__album_data['artist']
            file_to_encode['album'] = self.__album_data['title']
            file_to_encode['date'] = self.__album_data['release_date'][2]
            file_to_encode.save()
            file_to_encode = MP3(file_name)
            print(self.__album_data['cover'])
            cover_data = open(self.__album_data['cover'], 'rb').read()
            file_to_encode.tags.add(
                APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc=u'Cover',
                    data=cover_data
                )
            )
            file_to_encode.save()
            i += 1
        print("\nEncoding finished!\n")

    def clean_up_files(self):
        """
        Deletes all temporary files that may have been
        created

        """
        file_list = [f for f in os.listdir(self.__directory) if f.endswith(".tmp")]

        for file in file_list:
            os.remove(self.__directory + "\\" + file)

    def open_file_path(self):
        """
        opens up the path to the downloaded files
        when program has finished downloading

        """
        if platform.system() == "Windows":
            os.startfile(self.__directory)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", self.__file_path])
