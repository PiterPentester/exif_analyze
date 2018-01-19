import sys, os
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QImage, QPainter, QPalette, QPixmap
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from time import *

def timeformat(time):
	local_tuple = localtime(time)
	time_format = "%Y/%m/%d %H:%M:%S"
	time_str = strftime(time_format, local_tuple)
	return time_str

def get_file_info(fname):
	result = os.stat(fname)
	size = result[6]
	atime = timeformat(result[7])
	mtime =timeformat(result[8])
	ctime = timeformat(result[9])
	return size, atime, mtime, ctime

class ImageMetaData(object):
	exif_data = None
	image = None

	def __init__(self, img_path):
		self.image = Image.open(img_path)
		self.get_exif_data()
		super(ImageMetaData, self).__init__()

	def get_exif_data(self):
		exif_data = {}
		info = self.image._getexif()
		if info:
			for tag, value in info.items():
				decoded = TAGS.get(tag, tag)
				if decoded == "GPSInfo":
					gps_data = {}
					for t in value:
						sub_decoded = GPSTAGS.get(t, t)
						gps_data[sub_decoded] = value[t]

					exif_data[decoded] = gps_data
				else:
					exif_data[decoded] = value
		self.exif_data = exif_data
		return exif_data

	def get_if_exist(self, data, key):
		if key in data:
			return data[key]
		return None

	def convert_to_degress(self, value):
		d0 = value[0][0]
		d1 = value[0][1]
		d = float(d0) / float(d1)

		m0 = value[1][0]
		m1 = value[1][1]
		m = float(m0) / float(m1)

		s0 = value[2][0]
		s1 = value[2][1]
		s = float(s0) / float(s1)

		return d + (m / 60.0) + (s / 3600.0)

	def get_lat_lng(self):
		lat = None
		lng = None
		exif_data = self.get_exif_data()

		if "GPSInfo" in exif_data:
			gps_info = exif_data["GPSInfo"]
			gps_latitude = self.get_if_exist(gps_info, "GPSLatitude")
			gps_latitude_ref = self.get_if_exist(gps_info, "GPSLatitudeRef")
			gps_longitude = self.get_if_exist(gps_info, "GPSLongitude")
			gps_longitude_ref = self.get_if_exist(gps_info, "GPSLongitudeRef")
			if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
				lat = self.convert_to_degress(gps_latitude)
				if gps_latitude_ref != "N":
					lat = 0 - lat
				lng = self.convert_to_degress(gps_longitude)
				if gps_longitude_ref != "E":
					lng = 0 - lng
		return lat, lng


class TabDialog(QDialog):
	def __init__(self, parent=None):
		super(TabDialog, self).__init__(parent)		

		tabWidget = QTabWidget()

		dirTab = DirectoryTab()
		exifTab = ExifTab(dirTab)

		tabWidget.addTab(dirTab, "Directory")
		tabWidget.addTab(exifTab, "Exif")

		buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

		buttonBox.accepted.connect(self.accept)
		buttonBox.rejected.connect(self.reject)

		mainLayout = QVBoxLayout()
		mainLayout.addWidget(tabWidget)
		mainLayout.addWidget(buttonBox)
		self.setLayout(mainLayout)

		self.setWindowTitle("Exif Parser")

		self.resize(1920,1080)


class DirectoryTab(QWidget):
	def __init__(self, parent=None):
		super(DirectoryTab, self).__init__(parent)
		self.flist = []
		self.directory = ""
		self.directoryButton = QPushButton("Select Directory")
		self.directoryButton.clicked.connect(self.setExistingDir)

		self.dirNameLabel = QLabel("Directory Name: ")
		self.dirValueLabel = QLabel(self.directory)
		self.dirValueLabel.setFrameStyle(QFrame.Panel | QFrame.Sunken)			

		self.mainLayout = QVBoxLayout()
		self.mainLayout.addWidget(self.dirNameLabel, 1, 0)
		self.mainLayout.addWidget(self.dirValueLabel, 1, 1)
		self.mainLayout.addWidget(self.directoryButton, 2, 0)		
		self.setLayout(self.mainLayout)

	def setExistingDir(self):
		options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
		directory = QFileDialog.getExistingDirectory(self,"Select Directory",self.dirValueLabel.text(), options=options)
		if directory:
			os.chdir(directory)
			self.dirValueLabel.setText(directory)
			tmp = os.listdir(directory)
			for f in tmp:
				ext = f.split(".")[-1].lower()
				if ext == "jpg" or ext == "jpeg":
					self.flist.append(f)

		self.questionMsg(directory)

	def questionMsg(self, directory):
		reply = QMessageBox.information(self, "Confirm", "'"+directory+"' selected!", QMessageBox.Yes | QMessageBox.No)
		if reply != QMessageBox.Yes:
			self.setExistingDir()
		else:
			self.createTable()
			self.mainLayout.addWidget(self.tableWidget, 3, 0)
			self.setLayout(self.mainLayout)

	def createTable(self):
		self.tableWidget = QTableWidget()
		self.tableWidget.setRowCount(len(self.flist)+1)
		self.tableWidget.setColumnCount(5)
		self.tableWidget.setItem(0,0,QTableWidgetItem("File"))
		self.tableWidget.setItem(0,1,QTableWidgetItem("Size"))
		self.tableWidget.setItem(0,2,QTableWidgetItem("atime"))
		self.tableWidget.setItem(0,3,QTableWidgetItem("mtime"))
		self.tableWidget.setItem(0,4,QTableWidgetItem("ctime"))		

		cnt = 1
		for f in self.flist:
			size, atime, mtime, ctime = get_file_info(f)
			self.tableWidget.setItem(cnt,0, QTableWidgetItem(f))
			self.tableWidget.setItem(cnt,1, QTableWidgetItem(str(size)))
			self.tableWidget.setItem(cnt,2, QTableWidgetItem(atime))
			self.tableWidget.setItem(cnt,3, QTableWidgetItem(mtime))
			self.tableWidget.setItem(cnt,4, QTableWidgetItem(ctime))			
			cnt += 1		
		self.tableWidget.move(0,0)
		self.tableWidget.doubleClicked.connect(self.on_click)			

	def on_click(self):
		for cur in self.tableWidget.selectedItems():			
			exifPop = ExifPopup(cur.text(), self)
			exifPop.setGeometry(100, 200, 100, 100)
			exifPop.show()


class ExifTab(QWidget):
	def __init__(self, dirTab, parent=None):
		super(ExifTab, self).__init__(parent)

		self.fileListLabel = QLabel("Image List")
		self.dirTab = dirTab
		self.button = QPushButton("reset")
		self.button.clicked.connect(self.createTable)
		self.initUI()				


	def initUI(self):
		self.createTable()
		mainLayout = QVBoxLayout()
		mainLayout.addWidget(self.fileListLabel)	
		mainLayout.addWidget(self.tableWidget)
		mainLayout.addWidget(self.button)		
		self.setLayout(mainLayout)		

	def createTable(self):
		self.tableWidget = QTableWidget()
		self.tableWidget.setRowCount(len(self.dirTab.flist))
		self.tableWidget.setColumnCount(1)
		cnt = 0
		for f in self.dirTab.flist:
			self.tableWidget.setItem(cnt,0, QTableWidgetItem(f))			
			cnt += 1		
		self.tableWidget.move(0,0)
		self.tableWidget.doubleClicked.connect(self.on_click)			

	def on_click(self):
		for cur in self.tableWidget.selectedItems():
			print(cur.row(), cur.column(),cur.text())

class ExifPopup(QDialog):
	def __init__(self, name, parent=None):
		super(ExifPopup, self).__init__(parent)
		self.name = name		
		self.title = name
		self.left = 10
		self.top = 10
		self.width = 1920
		self.height = 1080
		self.initUI()

	def initUI(self):
		self.setWindowTitle(self.title)
		self.setGeometry(self.left, self.top, self.width, self.height)

		label = QLabel(self)
		pixmap = QPixmap(self.name)
		label.setPixmap(pixmap)
		self.resize(self.width/2, self.height/2)

		self.show()



if __name__ == "__main__":
	app = QApplication(sys.argv)
	dialog = TabDialog()
	dialog.show()
	sys.exit(app.exec_())





