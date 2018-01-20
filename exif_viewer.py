import sys, os
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QImage, QPainter, QPalette, QPixmap, QStandardItemModel
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from time import *
from functools import partial

option_lst = []

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


class MainDialog(QDialog):
    flist = []
    name, size, atime, mtime, ctime = range(5)

    def __init__(self, parent=None):
        super(MainDialog, self).__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("EXIF Viewer")        

        path = ""
        dirName = QLabel("Path ")
        dirValue = QLabel(path)
        dirValue.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        dirButton = QPushButton("Path..")
        dirButton.clicked.connect(partial(self.setExistingDir, dirValue))

        grpButton = QPushButton("Group")
        grpButton.clicked.connect(self.buildPopup)


        dirLayout = QGridLayout()
        dirLayout.setAlignment(Qt.AlignLeft)
        dirLayout.addWidget(dirName,0,0, Qt.AlignLeft)
        dirLayout.addWidget(dirValue,0,1, Qt.AlignLeft)
        dirLayout.addWidget(dirButton,0,2, Qt.AlignLeft)  
        dirLayout.addWidget(grpButton,0,3, Qt.AlignRight)      

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        buttonBox.accepted.connect(self.accept)

        dView = QTreeView()
        dView.setRootIsDecorated(False)
        dView.setAlternatingRowColors(True)
        dView.doubleClicked.connect(partial(self.selectImg, dView))

        self.model = self.createModel(self)
        dView.setModel(self.model)

        topLayout = QHBoxLayout()
        topLayout.addWidget(dView)        

        midLayout = QHBoxLayout()

        botLayout = QHBoxLayout()

        mainLayout = QVBoxLayout()
        mainLayout.setAlignment(Qt.AlignLeft)

        mainLayout.addLayout(dirLayout)
        mainLayout.addLayout(topLayout)
        mainLayout.addLayout(midLayout)
        mainLayout.addLayout(botLayout)
        mainLayout.addWidget(buttonBox)

        self.setLayout(mainLayout)
        self.resize(1920,1080)

        self.show()

    def buildPopup(self):        
        opPopup = option(self)
        opPopup.setGeometry(100,200,100,100)
        opPopup.show()

    def createModel(self, parent):
        model = QStandardItemModel(0, 5, parent)
        model.setHeaderData(self.name, Qt.Horizontal, "Name")
        model.setHeaderData(self.size, Qt.Horizontal, "Size")
        model.setHeaderData(self.atime, Qt.Horizontal, "atime")
        model.setHeaderData(self.mtime, Qt.Horizontal, "mtime")
        model.setHeaderData(self.ctime, Qt.Horizontal, "ctime")
        return model

    def addData(self, model, name, size, atime, mtime, ctime):
        model.insertRow(0)
        model.setData(model.index(0, self.name), name)
        model.setData(model.index(0, self.size), size)
        model.setData(model.index(0, self.atime), atime)
        model.setData(model.index(0, self.mtime), mtime)
        model.setData(model.index(0, self.ctime), ctime)

    def createTree(self):
        for f in self.flist:
            size, atime, mtime, ctime = get_file_info(f)
            self.addData(self.model, f, size, atime, mtime, ctime)

    def selectImg(self, dView):
        indexes = dView.selectedIndexes()
        index_list = [i.data() for i in dView.selectedIndexes()]

        imgPop = ImgPopup(index_list[0], self)
        imgPop.show()

    def setExistingDir(self, dirValue):
        options = QFileDialog.DontResolveSymlinks | QFileDialog.ShowDirsOnly
        directory = QFileDialog.getExistingDirectory(self,"Select Path",dirValue.text(), options=options)
        if directory:
            os.chdir(directory)
            dirValue.setText(directory)
            tmp = os.listdir(directory)
            for f in tmp:
                ext = f.split(".")[-1].lower()
                if ext == "jpg" or ext == "jpeg":
                    self.flist.append(f)

        self.questionMsg(directory, dirValue)

    def questionMsg(self, directory, dirValue):
        reply = QMessageBox.information(self, "Confirm", "\n'"+directory+"' selected!", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            self.flist = []
            self.setExistingDir(dirValue)
        else:
            os.chdir(directory)
            self.createTree()                    
            self.show()

class ImgPopup(QDialog):
    key, val = range(2)
    def __init__(self, name, parent=None):
        super(ImgPopup, self).__init__(parent)
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

        lay = QHBoxLayout()
        #lay.setAlignment(Qt.AlignLeft)
        imgLabel = QLabel()

        pixmap = QPixmap(self.name)
        pixmap = pixmap.scaled(640, 480, Qt.KeepAspectRatio)
        imgLabel.setPixmap(pixmap)  
        lay.addWidget(imgLabel)        

        img = ImageMetaData(self.name)            
        eTree = QTreeView()
        eTree.setRootIsDecorated(False)
        eTree.setAlternatingRowColors(True)

        self.model = self.createModel(self)
        eTree.setModel(self.model)

        exifLayout = QHBoxLayout()
        self.createTree(img)
        exifLayout.addWidget(eTree)        
        #exifLayout.addWidget(label)

        #lay.addWidget(self.tableWidget, 3)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttonBox.rejected.connect(self.reject) 

        #btnLayout = QGridLayout()
        #btnLayout.setAlignment(Qt.AlignRight)
        #btnLayout.addWidget(buttonBox,0,0)

        imgLayout = QVBoxLayout()
        imgLayout.setAlignment(Qt.AlignLeft)

        
        #imgLayout.addWidget(label)
        imgLayout.addLayout(lay)
        imgLayout.addLayout(exifLayout) 
        imgLayout.addWidget(buttonBox)       
        #imgLayout.addLayout(btnLayout)

        self.setLayout(imgLayout)

        self.show()

    def createModel(self, parent):
        model = QStandardItemModel(0, 2, parent)
        model.setHeaderData(self.key, Qt.Horizontal, "Tag")
        model.setHeaderData(self.val, Qt.Horizontal, "Value")
        return model

    def addData(self, model, key, val):
        self.model.insertRow(0)
        self.model.setData(model.index(0, self.key), key)
        self.model.setData(model.index(0, self.val), val)

    def createTree(self, img):
        exif = img.get_exif_data()
        exif_keys = exif.keys()

        lat, lng = img.get_lat_lng()

        for key in exif_keys:
            try:
                if key != "GPSInfo":
                    self.addData(self.model, key, str(exif[key])) 
                else:
                    if lat and lng:
                        for k in exif[key].keys():
                            if k == "GPSLatitude":
                                self.addData(self.model, k, str(lat))
                            elif k == "GPSLongitude":
                                self.addData(self.model, k, str(lng))
                            else:
                                self.addData(self.model, k, str(exif[key][k]))
                    else:
                        for k in exif[key].keys():
                            self.addData(self.model, k, str(exif[key][k]))                               
            except:
                pass        

    def createTable(self, img):
        exif = img.get_exif_data()
        exif_keys = exif.keys()

        self.tableWidget = QTableWidget()
        self.tableWidget.setRowCount(len(exif_keys)+1)
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setItem(0,0,QTableWidgetItem("Key"))
        self.tableWidget.setItem(0,1,QTableWidgetItem("Val"))

        cnt = 1
        for key in exif_keys:
            try:
                self.tableWidget.setItem(cnt, 0, QTableWidgetItem(key))
                print(type(exif[key]))
                self.tableWidget.setItem(cnt, 1, QTableWidgetItem(str(exif[key])))
                cnt += 1
            except:
                pass


class option(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        flag = 0
        state = False
        self.option_flag = []
        self.option_flag.append(False)
        self.option_flag.append(False)
        self.option_flag.append(False)
        self.option_flag.append(False)

        layout = QGridLayout()
        self.setLayout(layout)

        self.setWindowTitle("Option")

        self.op1 = QCheckBox("Make/Model")
        self.op1.setEnabled(True)
        self.op1.toggled.connect(partial(self.op_chk,0))
        layout.addWidget(self.op1, 0,0)

        self.op2 = QCheckBox("DateChanged")
        self.op2.setEnabled(True)
        self.op2.toggled.connect(partial(self.op_chk,1))
        layout.addWidget(self.op2, 0,1)

        self.op3 = QCheckBox("Size")
        self.op3.setEnabled(True)
        self.op3.toggled.connect(partial(self.op_chk,2))
        layout.addWidget(self.op3, 0,2)

        self.op4 = QCheckBox("Software")
        self.op4.setEnabled(True)
        self.op4.toggled.connect(partial(self.op_chk,3))
        layout.addWidget(self.op4, 0,3)

        button = QPushButton("OK")
        button.clicked.connect(self.buildPopup)

        layout.addWidget(button, 1,0)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttonBox.rejected.connect(self.reject) 

        layout.addWidget(buttonBox, 1,1)        

    def buildPopup(self):
        option_lst.clear()
        for b in self.option_flag:
            option_lst.append(b)
        grp = groupPop(self)        
        grp.setGeometry(10,10,1920,1080)
        grp.show()

    def op_chk(self, idx):
        if self.option_flag[idx] == True:
            self.option_flag[idx] = False
        else:
            self.option_flag[idx] = True

    def test(self):
        print(self.option_flag)

    def make_model_cmp(self):
        print(os.getcwd())

class groupPop(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)       
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Group")

        self.createTable()        

        buttonBox = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttonBox.rejected.connect(self.reject)

        labelLayout = QHBoxLayout()
        modelLabel = QLabel("Model")
        modelLabel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        makeLabel = QLabel("Make")
        makeLabel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        dateLabel = QLabel("Date")
        dateLabel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        sizeLabel = QLabel("Size")
        sizeLabel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        softLabel = QLabel("Software")
        softLabel.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        self.layout = QVBoxLayout()
        self.layout.addLayout(labelLayout)

        tableLayout = QHBoxLayout()
        if option_lst[0] == True:
            labelLayout.addWidget(modelLabel)
            labelLayout.addWidget(makeLabel)
            tableLayout.addWidget(self.mmTable)
            tableLayout.addWidget(self.makeTable)
        if option_lst[1] == True:
            labelLayout.addWidget(dateLabel)
            tableLayout.addWidget(self.dateTable)
        if option_lst[2] == True:
            labelLayout.addWidget(sizeLabel)
            tableLayout.addWidget(self.sizeTable)
        if option_lst[3] == True:
            labelLayout.addWidget(softLabel)
            tableLayout.addWidget(self.softwareTable)

        self.layout.addLayout(tableLayout)
        self.layout.addWidget(buttonBox)

        self.setLayout(self.layout)

    def createTable(self):
        self.flist = []
        self.model = []
        self.model_g = {}
        self.make = []
        self.make_g = {}
        self.date = {}
        self.size= {}
        self.software = []
        self.software_g = {}

        self.date.update({"Original":[]})
        self.date.update({"Modified":[]})

        self.size.update({"Original":[]})
        self.size.update({"Modified":[]})

        tmp = os.listdir(os.getcwd())
        for f in tmp:
            ext = f.split(".")[-1].lower()
            if ext == "jpg" or ext == "jpeg":
                self.flist.append(f) 

        self.img = []
        for f in self.flist:
            self.img.append(ImageMetaData(f))    

        for i in self.img:
            d = i.get_exif_data()
            #print(d['Model'], d['Make'])

        if option_lst[0] == True:
            self.grp_make_model()

        if option_lst[1] == True:
            self.grp_date()

        if option_lst[2] == True:
            self.grp_size()

        if option_lst[3] == True:
            self.grp_software()

    def grp_make_model(self):
        for i in range(len(self.img)):
            d = self.img[i].get_exif_data()
            if 'Model' in d.keys():
                if d['Model'] in self.model:
                    self.model_g[d['Model']].append(self.flist[i])
                else:
                    self.model.append(d['Model'])
                    self.model_g.update({d['Model']:[self.flist[i]]})
            if 'Make' in d.keys():
                if d['Make'] in self.make:
                    self.make_g[d['Make']].append(self.flist[i])
                else:
                    self.make.append(d['Make'])
                    self.make_g.update({d['Make']:[self.flist[i]]})

        self.mmTable = QTableWidget()        
        self.mmTable.setRowCount(len(self.flist))
        self.mmTable.setColumnCount(2)

        self.mmTable.setHorizontalHeaderLabels(["[Model]", "[File]"])

        cnt = 0
        for i in self.model_g.keys():
            self.mmTable.setItem(cnt, 0, QTableWidgetItem(str(i)))                        
            for m in self.model_g[i]:                                
                self.mmTable.setItem(cnt, 1, QTableWidgetItem(str(m)))
                cnt += 1

        self.makeTable = QTableWidget()
        self.makeTable.setRowCount(len(self.flist))
        self.makeTable.setColumnCount(2)

        self.makeTable.setHorizontalHeaderLabels(["[Make]","[File]"])
        cnt = 0        
        for i in self.make_g.keys():
            self.makeTable.setItem(cnt, 0, QTableWidgetItem(str(i)))
            for m in self.make_g[i]:
                self.makeTable.setItem(cnt, 1, QTableWidgetItem(str(m)))
                cnt += 1

    def grp_date(self):
        for i in range(len(self.img)):            
            d = self.img[i].get_exif_data()
            date = ""
            date_ori = ""
            date_dig = ""

            if "DateTime" in d.keys():
                date = d["DateTime"]
            if "DateTimeOriginal" in d.keys():
                date_ori = d["DateTimeOriginal"]
            if "DateTimeDigitized" in d.keys():
                date_dig = d["DateTimeDigitized"]

            if date == date_ori:
                if date == date_dig:
                    self.date["Original"].append(self.flist[i])
                else:
                    self.date["Modified"].append(self.flist[i])
            else:
                self.date["Modified"].append(self.flist[i])

        self.dateTable = QTableWidget()
        self.dateTable.setRowCount(len(self.flist))
        self.dateTable.setColumnCount(2)

        self.dateTable.setHorizontalHeaderLabels(["[Date]","[File]"])
        
        cnt = 0
        self.dateTable.setItem(cnt, 0, QTableWidgetItem("Original"))
        #cnt += 1
        for m in self.date["Original"]:
            self.dateTable.setItem(cnt, 1, QTableWidgetItem(m))
            cnt += 1

        self.dateTable.setItem(cnt, 0, QTableWidgetItem("Modified"))
        #cnt += 1
        for m in self.date["Modified"]:
            self.dateTable.setItem(cnt, 1, QTableWidgetItem(m))
            cnt += 1

    def grp_size(self):
        "ExifImageWidth", "ExifImageHeight"
        for i in range(len(self.img)):
            width, height = self.img[i].image.size
            d = self.img[i].get_exif_data()

            if "ExifImageWidth" in d.keys() and "ExifImageHeight" in d.keys():
                exif_w = d["ExifImageWidth"]
                exif_h = d["ExifImageHeight"]

                if width != exif_w or height != exif_h:
                    self.size["Modified"].append(self.flist[i])
                else:
                    self.size["Original"].append(self.flist[i])

        self.sizeTable = QTableWidget()
        self.sizeTable.setRowCount(len(self.flist))
        self.sizeTable.setColumnCount(2)

        self.sizeTable.setHorizontalHeaderLabels(["[Size]","[File]"])

        cnt = 0
        self.sizeTable.setItem(cnt,0,QTableWidgetItem("Original"))

        for m in self.size["Original"]:
            self.sizeTable.setItem(cnt,1,QTableWidgetItem(str(m)))
            cnt += 1

        self.sizeTable.setItem(cnt,0,QTableWidgetItem("Modified"))
        for m in self.size["Modified"]:
            self.sizeTable.setItem(cnt,1,QTableWidgetItem(str(m)))
            cnt += 1

    def grp_software(self):
        for i in range(len(self.img)):            
            d = self.img[i].get_exif_data()
            if "Software" in d.keys():
                software = d["Software"]
                if software in self.software:
                    self.software_g[software].append(self.flist[i])
                else:
                    self.software.append(software)
                    self.software_g.update({software:[self.flist[i]]})

        self.softwareTable = QTableWidget()
        self.softwareTable.setRowCount(len(self.flist))
        self.softwareTable.setColumnCount(2)

        self.softwareTable.setHorizontalHeaderLabels(["[Software]","[File]"])

        cnt = 0

        for m in self.software:
            self.softwareTable.setItem(cnt,0,QTableWidgetItem(m))
            for n in self.software_g[m]:
                self.softwareTable.setItem(cnt,1,QTableWidgetItem(n))
                cnt += 1






        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = MainDialog()
    sys.exit(app.exec_())

