import sys

from PyQt4 import QtGui
from PyQt4 import QtCore

import bandloader_gui
import bandloader


class MainUiClass(QtGui.QMainWindow, bandloader_gui.Ui_MainWindow):

    def __init__(self, parent=None):
        super(MainUiClass, self).__init__(parent)
        self.usr_dir = ""
        self.cover_url = 0
        self.setupUi(self)

        # Connect the buttons to methods
        self.download_button.clicked.connect(self.begin_download)
        self.dir_button.clicked.connect(self.get_dir)
        self.clear_button.clicked.connect(self.clear_field)
        self.action_clear_all.triggered.connect(self.clear_all)
        self.action_quit.triggered.connect(self.quit_meth)

    def display_error(self, error):
        if error == 1:
            QtGui.QMessageBox.about(self, "Error", "Missing either Directory or\n"
                                                    "Bandcamp URL")

        elif error == 2:
            QtGui.QMessageBox.about(self, "Error", "Invalid Bandcamp URL\n"
                                                    "URL must be in this format:\n"
                                                    "https://____.bandcamp.com/album/____")
        elif error == 3:
            QtGui.QMessageBox.about(self, "Continue?", "No links found for track:\n" +
                                    str(self.invalid_tracks).replace("'", "").
                                    replace("[", "").replace("]", ""))

    def clear_all(self):
        """
        Triggered when user clicks the
        File -> Clear All option

        Clears all the fields
        """
        self.url_edit.setText("")
        self.dir_edit.setText("")

    def quit_meth(self):
        """
        Triggered when user clicks the
        File -> Quit option

        Quits the application, prompts the user
        """
        choice = QtGui.QMessageBox.question(self,
                                            'Quit',
                                            'Are you sure you want to quit?\n',
                                            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if choice == QtGui.QMessageBox.Yes:
            sys.exit(0)
        else:
            pass

    def clear_field(self):
        """
        Triggered when clicking clear button

        Clears the URL field
        """
        self.url_edit.setText("")

    def update_progress_bar(self, prog):
        """
        Update the progress bar

        :param prog:
        :return:
        """

        self.progress = prog / len(self.album['track_titles']) * 100

        if self.progress == 100:
            self.progress = 90

        self.progress_bar.setValue(self.progress)

    def show_track_downloading(self, track_num):
        """
        Tell the user what track were downloading

        :param trackNum:
        :return:
        """
        track = track_num - 1
        self.progress_label.setText("Downloading track: " + self.album['track_titles'][track] + "\nThis takes a bit...")


    def get_dir(self):
        """
        Triggered when clicking on the browse dir button

        Opens up explorer for user to select
        the directory they would like to save the
        files to

        Then sets the dir_labe in the GUI to said directory
        """
        self.usr_dir = QtGui.QFileDialog.getExistingDirectory(self,
                                                              'Select where to '
                                                              'save files')
        self.dir_edit.setText(self.usr_dir)

    def toggle_buttons(self, type_toggle):
        self.download_button.setEnabled(type_toggle)
        self.dir_edit.setEnabled(type_toggle)
        self.url_edit.setEnabled(type_toggle)
        self.dir_button.setEnabled(type_toggle)
        self.clear_button.setEnabled(type_toggle)

    def begin_download(self):
        url = str(self.url_edit.text())
        file_dir = str(self.dir_edit.text())

        if not url or not file_dir:
            self.display_error(error=1)
        elif "/album/" not in url:
            self.display_error(error=2)
        else:
            self.toggle_buttons(False)
            self.album, self.invalid_tracks = bandloader.collect_album_info(url)

            if self.invalid_tracks:
                self.display_error(3)

            self.final_dir = bandloader.create_dir(file_dir, self.album['title'])
            self.d_thread = DownloadThread(album_data=self.album, directory=self.final_dir)
            self.connect(self.d_thread, QtCore.SIGNAL('PROGRESS'), self.update_progress_bar)
            self.connect(self.d_thread, QtCore.SIGNAL('PROGRESS'), self.show_track_downloading)
            self.connect(self.d_thread, QtCore.SIGNAL('THREAD DONE'), self.finish_up)
            # Start download thread
            self.d_thread.start()

            # Check to see if we have a url to download the album cover with
            if not self.album['cover_url']:
                QtGui.QMessageBox.about(self, "Dang!", "No album cover found\n"
                                                       "Continuing...")
                self.cover_url = -1

    def finish_up(self):
        """
        Do finishing tasks, such as download album cover,
        encode tracks, stop threads, and clean up directory

        """

        # Stop the thread
        self.d_thread.quit()

        # Skip downloading cover URL if we don't have it
        if self.cover_url == -1:
            print("Cant download cover")
        else:
            self.progress_label.setText("Downloading album cover.")
            self.album['cover'] = self.download_cover(self.album['cover_url'], self.final_dir)

        # Encode the mp3 files
        self.progress_label.setText("Encoding files...")
        self.encode(self.album, self.final_dir)

        # Clean up files
        bandloader.clean_up_files(self.final_dir)

        # Finish the progress bar
        self.progress_bar.setValue(100)
        QtGui.QMessageBox.about(self, "Done", "Done downloading & encoding!\n"
                                              "Remember, please support the Artists")
        self.progress_label.setText("Done!")
        self.toggle_buttons(True)
        bandloader.open_file_path(self.final_dir)

    @staticmethod
    def download_cover(cover_url, directory):
        """
        Downloads the album cover after downloading tracks
        """
        result = bandloader.download_album_cover(cover_url, directory)

        return result

    @staticmethod
    def encode(album, directory):
        """
        Encodes the tracks using mutagen
        """
        bandloader.encode_tracks(album, directory)


class DownloadThread(QtCore.QThread):

    """
    Threading for the download function inside of
    bandloader.py

    Without threading GUI locks up :(

    We grab
    """

    def __init__(self, parent=None, album_data=None, directory=None):
        super(DownloadThread, self).__init__(parent)
        self.album_info = album_data
        self.directory = directory

    def run(self):
        i = 0
        perc = 0
        for track in self.album_info['track_info']:
            perc += 1
            self.emit(QtCore.SIGNAL('PROGRESS'), perc)
            bandloader.download_tracks(track, self.album_info['track_titles'][i],
                                                self.directory)

            i += 1

        self.emit(QtCore.SIGNAL('THREAD DONE'))


if __name__ == '__main__':
    a = QtGui.QApplication(sys.argv)
    app = MainUiClass()
    palette = QtGui.QPalette()
    palette.setBrush(QtGui.QPalette.Background, QtGui.QBrush(QtGui.QPixmap("Assets/background.png")))
    app.setPalette(palette)
    app.show()
    a.exec()
