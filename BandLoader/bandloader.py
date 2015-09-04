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


def get_track_titles(tracks):
    """
    Gets track titles and appends it to a new
    list, returns list

    Also fixes the track titles and removes any invalid file names that it may have

    For example chars such as *, /, ?
    are removed from the name, so that when it saves the mp3
    file we dont get an error

    :param tracks:
    :return:
    """
    track_t = []
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    for track in tracks:
        valid_track_name = track['title']
        track['title'] = ''.join(c for c in valid_track_name if c in valid_chars)
        track_t.append(track['title'])

    return track_t


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


def create_dir(directory, album_title):
    """
    Create the directory for saving downloaded files


    :param directory: sent directory that user selected
    :param album_title: title of the album (folder name)
    :return: file_path
    """
    file_path = directory + "\\" + album_title + "\\"
    print(file_path)

    if not os.path.exists(file_path):
        os.makedirs(file_path)
    os.path.expanduser(file_path)

    return file_path


def collect_album_info(url):
    """
    Collects information by crawiling through the website
    stores information into album_data dictionary and then
    returns information

    :param url:
    :return album_data:
    """
    tmp_site = urllib.request.urlopen(url)
    site_source = tmp_site.read().decode('utf-8')
    tmp_site.close()
    album_data = {}
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    album_data['track_info'] = get_html_data('trackinfo', site_source, True)
    album_data['track_titles'] = get_track_titles(album_data['track_info'])
    album_data['artist'] = get_html_data("artist", site_source).replace('"', '')
    album_data['artist'] = ''.join(c for c in album_data['artist'] if c in valid_chars)
    album_data['title'] = get_html_data("album_title", site_source).replace('"', '')
    album_data['title'] = ''.join(c for c in album_data['title'] if c in valid_chars)
    album_data['release_date'] = get_html_data("release_date", site_source).replace('"', '')
    album_data['cover_url'] = get_html_data("artFullsizeUrl", site_source).replace('"', '')
    album_data['release_date'] = fix_release_date(album_data['release_date'])
    return album_data


def download_tracks(track_info, track_title, directory):
    """
    Downloads the track that was sent to it
    Skips over tracks that have alread been downloaded

    :param track_info:
    :param track_titles:
    :param directory:
    :return:
    """
    print("Downloading....")
    # If we cant find the URL to download skip MP3
    if not track_info['file']:
        print("error")
        return track_title
    else:
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


def download_album_cover(album_cover, directory):
    """
    Downloads album cover from URL
    :param album_cover:
    :param directory:
    :return:
    """
    print("\nDownloading album cover...\n")
    tmp_file = wgetter.download(album_cover, outdir=directory)
    file_name = directory + "\\" + "cover.jpg"
    # if file already exists, we skip that file and delete the tmp_file
    if os.path.isfile(file_name):
        os.remove(tmp_file)
        print("Skipping file: " + file_name + " already exists.")
        return file_name
    else:
        os.rename(tmp_file, file_name)
        print("\nDone downloading album cover!\n")
        return file_name


def encode_tracks(album_info, directory):
    """
    Using mutagen this encodes the .MP3
    files so that Itunes and other
    players can know what Artist,
    album, etc are.

    :param album_info:
    :param directory:
    :return:
    """
    print("Encoding...")
    i = 0
    for track in album_info['track_titles']:
        file_name = directory + track + ".mp3"
        try:
            file_to_encode = EasyID3(file_name)
        except mutagen.id3.ID3NoHeaderError:
            print("\nFile didnt have ID3 tag, tagging now\n")
            file_to_encode = mutagen.File(file_name, easy=True)
            file_to_encode.add_tags()
        # add the mp3 tags to the audio files
        file_to_encode['tracknumber'] = str((i + 1))
        file_to_encode['title'] = track
        file_to_encode['artist'] = album_info['artist']
        file_to_encode['album'] = album_info['title']
        file_to_encode['date'] = album_info['release_date'][2]
        file_to_encode.save()
        file_to_encode = MP3(file_name)
        print(album_info['cover'])
        cover_data = open(album_info['cover'], 'rb').read()
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


def clean_up_files(path):
    """
    Deletes all temporary files that may have been
    created

    :param path:
    :return:
    """
    file_list = [f for f in os.listdir(path) if f.endswith(".tmp")]

    for file in file_list:
        os.remove(path + "\\" + file)


# opens up the path to the downloaded files
# when program has finished downloading
def open_file_path(path):
    """
    opens up the path to the downloaded files
    when program has finished downloading

    :param path:
    :return:
    """
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])

