from distutils.core import setup
import py2exe

setup(options={"py2exe":{"optimize": 2, "bundle_files": 0, "includes": ["sip"]}}, windows=[{'script': 'main.py', 'icon_resources':[(1, 'D:/Programming Projects/Python Projects/BandLoader/BandLoader/Assets/applogo.ico')]}], 
	version=1.5, author='Luis P.', author_email="luispadronn@gmail.com", description="Python application that scrapes and downloads from Bandcamp.com", 
	data_files=[('Assets', ['D:/Programming Projects/Python Projects/BandLoader/BandLoader/Assets/background.png'])] ,zipfile = None)