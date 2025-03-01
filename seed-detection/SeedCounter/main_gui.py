import camera_gp as camera
import tkinter as tk
import gphoto2 as gp
import io
from tkinter import *
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import time
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
camera_fps= 0.5

camera = camera.CanonCamera()
isFirstCaptured = False

import cv2
from skimage import filters
import matplotlib.pyplot as pyplt
import numpy as np

from sklearn.cluster import KMeans
from process import tkintercorestat
from process import tkintercore
from utils import cal_kernelsize

import os
import csv
import scipy.linalg as la
import multiprocessing
import time

import sys

batchfilepath = ''
inputfolder = ''
outputfolder = ''

print('Number of arguments:', len(sys.argv), 'arguments.')
print('Argument List:')
args = list(sys.argv)
for i in range(1, len(args)):
    print(args[i])

cwd = os.getcwd()
batchfilepath = cwd + '/' + "test/config/test-batch.txt"
print('batchfilepath', batchfilepath)
inputfolder = cwd + '/' + "test/input/"
print('inputfolder', inputfolder)
outputfolder = cwd + '/' + "test/output"
print('outputfolder', outputfolder)

batch_colorbandtable = np.array(
    [[255, 0, 0], [255, 127, 0], [255, 255, 0], [127, 255, 0], [0, 255, 255], [0, 127, 255], [0, 0, 255], [127, 0, 255],
     [75, 0, 130], [255, 0, 255]], 'uint8')

batch_filenames = []
pcweight = 0
pcs = 0
kmeans = 0
kmeans_sel = []
maxthres = 0
minthres = 0
maxlw = 0
minlw = 0
std_nonzeroratio = 0


def Open_batchfile():
    global pcs, pcweight, kmeans, kmeans_sel, maxthres, minthres, maxlw, minlw, std_nonzeroratio
    btfile = batchfilepath
    if len(btfile) > 0:
        if '.txt' in btfile:
            with open(btfile, mode='r') as f:
                setting = f.readlines()
                # print(setting)
                pcweight = float(setting[0].split(',')[1])
                pcs = int(setting[1].split(',')[1]) + 1
                # print(pcs)
                # for i in range(len(pcs)):
                #     pcs[i]=int(pcs[i])
                kmeans = setting[2].split(',')[1]
                kmeans = int(kmeans)
                kmeans_sel = setting[3].split(',')[1:-1]
                maxthres = setting[4].split(',')[1]
                try:
                    maxthres = float(maxthres)
                except:
                    print('Load Max area error', 'No Max area threshold value.')
                    return
                minthres = setting[5].split(',')[1]
                minthres = float(minthres)
                maxlw = setting[6].split(',')[1]
                maxlw = float(maxlw)
                minlw = setting[7].split(',')[1]
                minlw = float(minlw)
                std_nonzeroratio = float(setting[8].split(',')[1])
                for i in range(len(kmeans_sel)):
                    kmeans_sel[i] = int(kmeans_sel[i])
                print('PCweight', pcweight, 'PCsel', pcs, 'KMeans', kmeans, 'KMeans-Selection', kmeans_sel)
                print('maxthres', maxthres, 'minthres', minthres, 'maxlw', maxlw, 'minlw', minlw)
                print('Batch settings',
                      'PCweight=' + str(pcweight) + '\nPCsel=' + str(pcs) + '\nKMeans=' + str(kmeans) +
                      '\nCluster selection' + str(kmeans_sel) + '\nMax area=' + str(maxthres) +
                      '\nMin area=' + str(minthres) + '\nMax diagonal=' + str(maxlw) + '\nMin diagonal=' +
                      str(minlw))


def batch_findratio(originsize, objectsize):
    oria = originsize[0]
    orib = originsize[1]
    obja = objectsize[0]
    objb = objectsize[1]
    if oria > obja or orib > objb:
        ratio = round(max((oria / obja), (orib / objb)))
    else:
        ratio = round(min((obja / oria), (objb / orib)))
    if oria * orib > 850 * 850:
        if ratio < 2:
            ratio = 2
    return ratio


def Open_batchfolder():
    global batch_filenames

    FOLDER = inputfolder
    if len(FOLDER) > 0:
        print(FOLDER)
        # for root, dirs,files in os.walk(FOLDER):
        files = os.listdir(FOLDER)
        for filename in files:
            # print('root',root)
            # print('dirs',dirs)
            # print("filename",filename)

            batch_filenames.append(filename)
            # batch_filenames.append(filename)
        #     Open_batchimage(FOLDER,filename)
        #     batch_singleband(filename)
        # messagebox.showinfo('Finish loading','Loading Image finished')
        # if len(batch_filenames)==0:
        #     messagebox.showerror('No file','No file under current folder')
        #     return
    batch_filenames.sort()
    print('total # files', len(batch_filenames))


class batch_img():
    def __init__(self, size, bands):
        self.size = size
        self.bands = bands


class batch_ser_func():
    def __init__(self, filename):
        self.file = filename
        self.folder = inputfolder
        self.exportpath = outputfolder
        self.batch_Multiimage = {}
        self.batch_Multigray = {}
        self.batch_Multitype = {}
        self.batch_Multiimagebands = {}
        self.batch_Multigraybands = {}
        self.batch_displaybandarray = {}
        self.batch_originbandarray = {}
        self.batch_originpcabands = {}
        self.batch_colordicesband = {}
        self.batch_results = {}
        self.kernersizes = {}
        self.reseglabels = None
        self.displayfea_l = 0
        self.displayfea_w = 0
        self.RGB_vector = None
        self.colorindex_vector = None
        self.displaypclagels = None

    def Open_batchimage(self):
        try:
            Filersc = cv2.imread(self.folder + '/' + self.file, flags=cv2.IMREAD_ANYCOLOR)
            height, width, channel = np.shape(Filersc)
            Filesize = (height, width)
            print('filesize:', height, width)
            RGBfile = cv2.cvtColor(Filersc, cv2.COLOR_BGR2RGB)
            Grayfile = cv2.cvtColor(Filersc, cv2.COLOR_BGR2Lab)
            Grayfile = cv2.cvtColor(Grayfile, cv2.COLOR_BGR2GRAY)
            Grayimg = batch_img(Filesize, Grayfile)
            RGBbands = np.zeros((channel, height, width))
            for j in range(channel):
                band = RGBfile[:, :, j]
                band = np.where(band == 0, 1e-6, band)
                RGBbands[j, :, :] = band
            RGBimg = batch_img(Filesize, RGBbands)
            tempdict = {self.file: RGBimg}
            self.batch_Multiimagebands.update(tempdict)
            tempdict = {self.file: Grayfile}
            self.batch_Multigray.update(tempdict)
            tempdict = {self.file: 0}
            self.batch_Multitype.update(tempdict)
            tempdict = {self.file: Grayimg}
            self.batch_Multigraybands.update(tempdict)
        except:
            # messagebox.showerror('Invalid Image Format','Cannot open '+filename)
            return False
        return True

    def fillbands(self, originbands, displaybands, vector, vectorindex, name, band):
        tempdict = {name: band}
        if name not in originbands:
            originbands.update(tempdict)
            image = cv2.resize(band, (self.displayfea_w, self.displayfea_l), interpolation=cv2.INTER_LINEAR)
            displaydict = {name: image}
            displaybands.update(displaydict)
            fea_bands = image.reshape((self.displayfea_l * self.displayfea_w), 1)[:, 0]
            vector[:, vectorindex] = vector[:, vectorindex] + fea_bands
        return

    def singleband(self):
        try:
            bands = self.batch_Multiimagebands[self.file].bands
        except:
            return
        channel, fea_l, fea_w = bands.shape
        print('bandsize', fea_l, fea_w)
        if fea_l * fea_w > 2000 * 2000:
            ratio = batch_findratio([fea_l, fea_w], [2000, 2000])
        else:
            ratio = 1
        print('ratio', ratio)

        originbands = {}
        displays = {}
        displaybands = cv2.resize(bands[0, :, :], (int(fea_w / ratio), int(fea_l / ratio)),
                                  interpolation=cv2.INTER_LINEAR)
        displayfea_l, displayfea_w = displaybands.shape
        self.RGB_vector = np.zeros((displayfea_l * displayfea_w, 3))
        self.colorindex_vector = np.zeros((displayfea_l * displayfea_w, 12))
        self.displayfea_l, self.displayfea_w = displaybands.shape
        self.RGB_vectorr = np.zeros((displayfea_l * displayfea_w, 3))
        self.colorindex_vector = np.zeros((displayfea_l * displayfea_w, 12))
        Red = bands[0, :, :]
        Green = bands[1, :, :]
        Blue = bands[2, :, :]
        self.fillbands(originbands, displays, self.RGB_vector, 0, 'Band1', Red)
        self.fillbands(originbands, displays, self.RGB_vector, 1, 'Band2', Green)
        self.fillbands(originbands, displays, self.RGB_vector, 2, 'Band3', Blue)

        # secondsmallest_R=np.partition(Red,1)[1][0]
        # secondsmallest_G=np.partition(Green,1)[1][0]
        # secondsmallest_B=np.partition(Blue,1)[1][0]

        # Red=Red+secondsmallest_R
        # Green=Green+secondsmallest_G
        # Blue=Blue+secondsmallest_B

        PAT_R = Red / (Red + Green)
        PAT_G = Green / (Green + Blue)
        PAT_B = Blue / (Blue + Red)

        ROO_R = Red / Green
        ROO_G = Green / Blue
        ROO_B = Blue / Red

        DIF_R = 2 * Red - Green - Blue
        DIF_G = 2 * Green - Blue - Red
        DIF_B = 2 * Blue - Red - Green

        GLD_R = Red / (np.multiply(np.power(Blue, 0.618), np.power(Green, 0.382)))
        GLD_G = Green / (np.multiply(np.power(Blue, 0.618), np.power(Red, 0.382)))
        GLD_B = Blue / (np.multiply(np.power(Green, 0.618), np.power(Red, 0.382)))

        self.fillbands(originbands, displays, self.colorindex_vector, 0, 'PAT_R', PAT_R)
        self.fillbands(originbands, displays, self.colorindex_vector, 1, 'PAT_G', PAT_G)
        self.fillbands(originbands, displays, self.colorindex_vector, 2, 'PAT_B', PAT_B)
        self.fillbands(originbands, displays, self.colorindex_vector, 3, 'ROO_R', ROO_R)
        self.fillbands(originbands, displays, self.colorindex_vector, 4, 'ROO_G', ROO_G)
        self.fillbands(originbands, displays, self.colorindex_vector, 5, 'ROO_B', ROO_B)
        self.fillbands(originbands, displays, self.colorindex_vector, 6, 'DIF_R', DIF_R)
        self.fillbands(originbands, displays, self.colorindex_vector, 7, 'DIF_G', DIF_G)
        self.fillbands(originbands, displays, self.colorindex_vector, 8, 'DIF_B', DIF_B)
        self.fillbands(originbands, displays, self.colorindex_vector, 9, 'GLD_R', GLD_R)
        self.fillbands(originbands, displays, self.colorindex_vector, 10, 'GLD_G', GLD_G)
        self.fillbands(originbands, displays, self.colorindex_vector, 11, 'GLD_B', GLD_B)

        NDI = 128 * ((Green - Red) / (Green + Red) + 1)
        VEG = Green / (np.power(Red, 0.667) * np.power(Blue, (1 - 0.667)))
        Greenness = Green / (Green + Red + Blue)
        CIVE = 0.44 * Red + 0.811 * Green + 0.385 * Blue + 18.7845
        MExG = 1.262 * Green - 0.844 * Red - 0.311 * Blue
        NDRB = (Red - Blue) / (Red + Blue)
        NGRDI = (Green - Red) / (Green + Red)

        colorindex_vector = np.zeros((displayfea_l * displayfea_w, 7))

        self.fillbands(originbands, displays, colorindex_vector, 0, 'NDI', NDI)
        self.fillbands(originbands, displays, colorindex_vector, 1, 'VEG', VEG)
        self.fillbands(originbands, displays, colorindex_vector, 2, 'Greenness', Greenness)
        self.fillbands(originbands, displays, colorindex_vector, 3, 'CIVE', CIVE)
        self.fillbands(originbands, displays, colorindex_vector, 4, 'MExG', MExG)
        self.fillbands(originbands, displays, colorindex_vector, 5, 'NDRB', NDRB)
        self.fillbands(originbands, displays, colorindex_vector, 6, 'NGRDI', NGRDI)

        rgb_M = np.mean(self.RGB_vector.T, axis=1)
        colorindex_M = np.mean(self.colorindex_vector.T, axis=1)
        print('rgb_M', rgb_M, 'colorindex_M', colorindex_M)
        rgb_C = self.RGB_vector - rgb_M
        colorindex_C = self.colorindex_vector - colorindex_M
        rgb_V = np.corrcoef(rgb_C.T)
        color_V = np.corrcoef(colorindex_C.T)
        rgb_std = rgb_C / np.std(self.RGB_vector.T, axis=1)
        color_std = colorindex_C / np.std(self.colorindex_vector.T, axis=1)
        rgb_eigval, rgb_eigvec = np.linalg.eig(rgb_V)
        color_eigval, color_eigvec = np.linalg.eig(color_V)
        print('rgb_eigvec', rgb_eigvec)
        print('color_eigvec', color_eigvec)
        featurechannel = 14
        pcabands = np.zeros((self.colorindex_vector.shape[0], featurechannel))
        for i in range(3):
            pcn = rgb_eigvec[:, i]
            pcnbands = np.dot(rgb_std, pcn)
            pcvar = np.var(pcnbands)
            print('rgb pc', i + 1, 'var=', pcvar)
            pcabands[:, i] = pcabands[:, i] + pcnbands
        pcabands[:, 1] = np.copy(pcabands[:, 2])
        pcabands[:, 2] = pcabands[:, 2] * 0
        for i in range(2, featurechannel):
            pcn = color_eigvec[:, i - 2]
            pcnbands = np.dot(color_std, pcn)
            pcvar = np.var(pcnbands)
            print('color index pc', i - 1, 'var=', pcvar)
            pcabands[:, i] = pcabands[:, i] + pcnbands

        displayfea_vector = np.concatenate((self.RGB_vector, self.colorindex_vector), axis=1)
        self.batch_originpcabands.update({self.file: displayfea_vector})
        pcabandsdisplay = pcabands.reshape(displayfea_l, displayfea_w, featurechannel)
        tempdictdisplay = {'LabOstu': pcabandsdisplay}
        self.batch_displaybandarray.update({self.file: tempdictdisplay})
        self.batch_originbandarray.update({self.file: originbands})

    def kmeansclassify(self):
        if kmeans == 0:
            print('Kmeans error', 'Kmeans should greater than 0')
            return None
        file = self.file
        originpcabands = self.batch_displaybandarray[file]['LabOstu']
        pcah, pcaw, pcac = originpcabands.shape
        tempband = np.zeros((pcah, pcaw, 1))
        if pcweight == 0.0:
            tempband[:, :, 0] = tempband[:, :, 0] + originpcabands[:, :, pcs]
        else:
            if pcweight < 0.0:
                rgbpc = originpcabands[:, :, 0]
            else:
                rgbpc = originpcabands[:, :, 1]
            rgbpc = (rgbpc - rgbpc.min()) * 255 / (rgbpc.max() - rgbpc.min())
            firstterm = abs(pcweight) * 2 * rgbpc
            colorpc = originpcabands[:, :, pcs]
            colorpc = (colorpc - colorpc.min()) * 255 / (colorpc.max() - colorpc.min())
            secondterm = (1 - abs(pcweight) * 2) * colorpc
            tempband[:, :, 0] = tempband[:, :, 0] + firstterm + secondterm
        self.displaypclagels = np.copy(tempband[:, :, 0])
        if kmeans == 1:
            print('kmeans=1')
            displaylabels = np.mean(tempband, axis=2)
            pyplt.imsave(file + '_k=1.png', displaylabels)
        else:
            if kmeans > 1:
                h, w, c = tempband.shape
                print('shape', tempband.shape)
                reshapedtif = tempband.reshape(tempband.shape[0] * tempband.shape[1], c)
                print('reshape', reshapedtif.shape)
                clf = KMeans(n_clusters=kmeans, init='k-means++', n_init=10, random_state=0)
                tempdisplayimg = clf.fit(reshapedtif)
                # print('label=0',np.any(tempdisplayimg==0))
                displaylabels = tempdisplayimg.labels_.reshape(
                    (self.batch_displaybandarray[self.file]['LabOstu'].shape[0],
                     self.batch_displaybandarray[self.file]['LabOstu'].shape[1]))

            clusterdict = {}
            displaylabels = displaylabels + 10
            for i in range(kmeans):
                locs = np.where(tempdisplayimg.labels_ == i)
                maxval = reshapedtif[locs].max()
                print(maxval)
                clusterdict.update({maxval: i + 10})
            print(clusterdict)
            sortcluster = list(sorted(clusterdict))
            print(sortcluster)
            for i in range(len(sortcluster)):
                cluster_num = clusterdict[sortcluster[i]]
                displaylabels = np.where(displaylabels == cluster_num, i, displaylabels)
        return displaylabels

    def generateimgplant(self, displaylabels):
        colordicesband = np.copy(displaylabels)
        tempdisplayimg = np.zeros((self.batch_displaybandarray[self.file]['LabOstu'].shape[0],
                                   self.batch_displaybandarray[self.file]['LabOstu'].shape[1]))
        colordivimg = np.zeros((self.batch_displaybandarray[self.file]['LabOstu'].shape[0],
                                self.batch_displaybandarray[self.file]['LabOstu'].shape[1]))
        for i in range(len(kmeans_sel)):
            sk = kmeans_sel[i]
            print("KKKKKKKK:" + str(sk))
            tempdisplayimg = np.where(displaylabels == sk, 1, tempdisplayimg)

        currentlabels = np.copy(tempdisplayimg)
        originbinaryimg = np.copy(tempdisplayimg)

        tempcolorimg = np.copy(displaylabels).astype('float32')
        ratio = batch_findratio([tempdisplayimg.shape[0], tempdisplayimg.shape[1]], [850, 850])

        if tempdisplayimg.shape[0] * tempdisplayimg.shape[1] < 850 * 850:
            tempdisplayimg = cv2.resize(tempdisplayimg,
                                        (int(tempdisplayimg.shape[1] * ratio), int(tempdisplayimg.shape[0] * ratio)))
            colordivimg = cv2.resize(tempcolorimg,
                                     (int(colordivimg.shape[1] * ratio), int(colordivimg.shape[0] * ratio)))
        else:
            tempdisplayimg = cv2.resize(tempdisplayimg,
                                        (int(tempdisplayimg.shape[1] / ratio), int(tempdisplayimg.shape[0] / ratio)))
            colordivimg = cv2.resize(tempcolorimg,
                                     (int(colordivimg.shape[1] / ratio), int(colordivimg.shape[0] / ratio)))
        binaryimg = np.zeros((tempdisplayimg.shape[0], tempdisplayimg.shape[1], 3))
        colordeimg = np.zeros((colordivimg.shape[0], colordivimg.shape[1], 3))
        locs = np.where(tempdisplayimg == 1)
        binaryimg[locs] = [240, 228, 66]
        for i in range(kmeans):
            locs = np.where(colordivimg == i)
            colordeimg[locs] = batch_colorbandtable[i]
        Image.fromarray(colordeimg.astype('uint8')).save(self.file + '-allcolorindex.png', "PNG")
        Image.fromarray((binaryimg.astype('uint8'))).save(self.file + '-binaryimg.png', "PNG")
        return currentlabels, originbinaryimg

    def resegment(self):
        if type(self.reseglabels) == type(None):
            return False
        labels = np.copy(self.reseglabels)
        reseglabels, border, colortable, labeldict = tkintercorestat.resegmentinput(labels, minthres, maxthres, minlw,
                                                                                    maxlw)
        self.batch_results.update({self.file: (labeldict, {})})
        return True

    def extraction(self, currentlabels):
        if kmeans == 1:
            print('Invalid Class #', '#Class = 1, try change it to 2 or more, and refresh Color-Index.')
            return False
        nonzeros = np.count_nonzero(currentlabels)
        print('nonzero counts', nonzeros)
        nonzeroloc = np.where(currentlabels != 0)
        try:
            ulx, uly = min(nonzeroloc[1]), min(nonzeroloc[0])
        except:
            print('Invalid Colorindices', 'Need to process colorindicies')
            return False
        rlx, rly = max(nonzeroloc[1]), max(nonzeroloc[0])
        nonzeroratio = float(nonzeros) / ((rlx - ulx) * (rly - uly))
        print(nonzeroratio)
        if nonzeroratio > std_nonzeroratio * 2:
            return False

        dealpixel = nonzeroratio * currentlabels.shape[0] * currentlabels.shape[1]
        ratio = 1
        if nonzeroratio <= 0.2:  # and nonzeroratio>=0.1:
            ratio = batch_findratio([currentlabels.shape[0], currentlabels.shape[1]], [1600, 1600])
            if currentlabels.shape[0] * currentlabels.shape[1] > 1600 * 1600:
                workingimg = cv2.resize(currentlabels,
                                        (int(currentlabels.shape[1] / ratio), int(currentlabels.shape[0] / ratio)),
                                        interpolation=cv2.INTER_LINEAR)
            else:
                # ratio=1
                # print('nonzeroratio',ratio)
                workingimg = np.copy(currentlabels)
            segmentratio = 0
        else:
            print('deal pixel', dealpixel)
            if dealpixel > 512000:
                if currentlabels.shape[0] * currentlabels.shape[1] > 850 * 850:
                    segmentratio = batch_findratio([currentlabels.shape[0], currentlabels.shape[1]], [850, 850])
                    if segmentratio < 2:
                        segmentratio = 2
                    workingimg = cv2.resize(currentlabels, (
                    int(currentlabels.shape[1] / segmentratio), int(currentlabels.shape[0] / segmentratio)),
                                            interpolation=cv2.INTER_LINEAR)
            else:
                segmentratio = 1
                # print('ratio',ratio)
                workingimg = np.copy(currentlabels)
        pixelmmratio = 1.0
        coin = False
        print('nonzeroratio:', ratio, 'segmentation ratio', segmentratio)
        print('workingimgsize:', workingimg.shape)
        pyplt.imsave('workingimg.png', workingimg)
        originlabels = None
        if originlabels is None:
            originlabels, border, colortable, originlabeldict = tkintercorestat.init(workingimg, workingimg, '',
                                                                                     workingimg, 10, coin)
        self.reseglabels = originlabels
        self.batch_results.update({self.file: (originlabeldict, {})})
        return True

    def savePCAimg(self, originfile):
        file = self.file
        path = self.exportpath
        originpcabands = self.batch_displaybandarray[file]['LabOstu']
        pcah, pcaw, pcac = originpcabands.shape
        tempband = np.zeros((pcah, pcaw))
        if pcweight == 0.0:
            tempband = tempband + originpcabands[:, :, pcs]
        else:
            if pcweight < 0.0:
                rgbpc = originpcabands[:, :, 0]
            else:
                rgbpc = originpcabands[:, :, 1]
            rgbpc = (rgbpc - rgbpc.min()) * 255 / (rgbpc.max() - rgbpc.min())
            firstterm = abs(pcweight) * 2 * rgbpc
            colorpc = originpcabands[:, :, pcs]
            colorpc = (colorpc - colorpc.min()) * 255 / (colorpc.max() - colorpc.min())
            secondterm = (1 - abs(pcweight) * 2) * colorpc
            tempband = tempband + firstterm + secondterm
        displaylabels = np.copy(tempband)

        if displaylabels.min() < 0:
            displaylabels = displaylabels - displaylabels.min()
        colorrange = displaylabels.max() - displaylabels.min()
        displaylabels = displaylabels * 255 / colorrange
        grayimg = Image.fromarray(displaylabels.astype('uint8'), 'L')
        originheight, originwidth = self.batch_Multigraybands[file].size
        origingray = grayimg.resize([originwidth, originheight], resample=Image.BILINEAR)
        origingray.save(path + '/' + originfile + '-PCAimg.png', "PNG")
        # addcolorstrip()
        return

    def showcounting(self, tup, number=True, frame=True, header=True, whext=False, blkext=False):
        labels = tup[0]
        colortable = tup[2]
        coinparts = tup[3]
        filename = tup[4]

        uniquelabels = list(colortable.keys())

        imgrsc = cv2.imread(inputfolder + '/' + filename, flags=cv2.IMREAD_ANYCOLOR)
        imgrsc = cv2.cvtColor(imgrsc, cv2.COLOR_BGR2RGB)
        imgrsc = cv2.resize(imgrsc, (labels.shape[1], labels.shape[0]), interpolation=cv2.INTER_LINEAR)
        image = Image.fromarray(imgrsc)
        if whext == True:
            # blkbkg=np.zeros((labels.shape[0],labels.shape[1],3),dtype='float')
            whbkg = np.zeros((labels.shape[0], labels.shape[1], 3), dtype='float')
            whbkg[:, :, :] = [255, 255, 255]
            itemlocs = np.where(labels != 0)
            # blkbkg[itemlocs]=imgrsc[itemlocs]
            whbkg[itemlocs] = imgrsc[itemlocs]
            image = Image.fromarray(whbkg.astype('uint8'))
        if blkext == True:
            blkbkg = np.zeros((labels.shape[0], labels.shape[1], 3), dtype='float')
            itemlocs = np.where(labels != 0)
            blkbkg[itemlocs] = imgrsc[itemlocs]
            blkbkg[itemlocs] = imgrsc[itemlocs]
            image = Image.fromarray(blkbkg.astype('uint8'))

        print('showcounting_resize', image.size)
        image.save('beforlabel.gif', append_images=[image])
        draw = ImageDraw.Draw(image)
        sizeuniq, sizecounts = np.unique(labels, return_counts=True)
        minsize = min(sizecounts)
        suggsize = int(minsize ** 0.5)
        if suggsize > 22:
            suggsize = 22
        if suggsize < 14:
            suggsize = 14
        font = ImageFont.truetype('cmb10.ttf', size=suggsize)

        for uni in uniquelabels:
            if uni != 0:
                pixelloc = np.where(labels == uni)
                try:
                    ulx = min(pixelloc[1])
                except:
                    continue
                uly = min(pixelloc[0])
                rlx = max(pixelloc[1])
                rly = max(pixelloc[0])
                midx = ulx + int((rlx - ulx) / 2)
                midy = uly + int((rly - uly) / 2)
                print(ulx, uly, rlx, rly)
                if frame == True:
                    draw.polygon([(ulx, uly), (rlx, uly), (rlx, rly), (ulx, rly)], outline='red')
                if number == True:
                    if uni in colortable:
                        canvastext = str(colortable[uni])
                    else:
                        canvastext = 'No label'
                    # if imgtypevar.get()=='0':
                    draw.text((midx - 1, midy + 1), text=canvastext, font=font, fill='white')
                    draw.text((midx + 1, midy + 1), text=canvastext, font=font, fill='white')
                    draw.text((midx - 1, midy - 1), text=canvastext, font=font, fill='white')
                    draw.text((midx + 1, midy - 1), text=canvastext, font=font, fill='white')
                    # draw.text((midx,midy),text=canvastext,font=font,fill=(141,2,31,0))
                    draw.text((midx, midy), text=canvastext, font=font, fill='black')

        if header == True:
            content = 'item count:' + str(len(uniquelabels)) + '\n File: ' + filename
            contentlength = len(content) + 50
            # rectext=canvas.create_text(10,10,fill='black',font='Times 16',text=content,anchor=NW)
            draw.text((10 - 1, 10 + 1), text=content, font=font, fill='white')
            draw.text((10 + 1, 10 + 1), text=content, font=font, fill='white')
            draw.text((10 - 1, 10 - 1), text=content, font=font, fill='white')
            draw.text((10 + 1, 10 - 1), text=content, font=font, fill='white')
            # draw.text((10,10),text=content,font=font,fill=(141,2,31,0))
            draw.text((10, 10), text=content, font=font, fill='black')
        # image.save(originfile+'-countresult'+extension,"JPEG")
        # firstimg=Multigraybands[currentfilename]
        # height,width=firstimg.size
        height, width, channel = self.batch_displaybandarray[filename]['LabOstu'].shape
        ratio = batch_findratio([height, width], [850, 850])
        # if labels.shape[0]*labels.shape[1]<850*850:
        #    disimage=image.resize([int(labels.shape[1]*ratio),int(labels.shape[0]*ratio)],resample=Image.BILINEAR)
        # else:
        #    disimage=image.resize([int(labels.shape[1]/ratio),int(labels.shape[0]/ratio)],resample=Image.BILINEAR)
        print('show counting ratio', ratio)
        if height * width < 850 * 850:
            print('showcounting small')
            disimage = image.resize([int(width * ratio), int(height * ratio)], resample=Image.BILINEAR)
        else:
            print('showcounting big')
            disimage = image.resize([int(width / ratio), int(height / ratio)], resample=Image.BILINEAR)
        print('showcounting shape', disimage.size)
        # displayoutput=ImageTk.PhotoImage(disimage)
        disimage.save('output.gif', append_images=[disimage])
        displayoutput = disimage
        # image.save('originoutput.gif',append_images=[image])
        return displayoutput, image, disimage

    def export_ext(self, whext=False, blkext=False):
        if len(batch_filenames) == 0:
            print('No files', 'Please load images to process')
            return
        file = self.file
        path = self.exportpath
        suggsize = 8
        smallfont = ImageFont.truetype('cmb10.ttf', size=suggsize)
        # kernersizes={}
        # for file in batch_filenames:
        labeldict = self.batch_results[file][0]
        itervalue = 'iter0'
        labels = labeldict[itervalue]['labels']
        counts = labeldict[itervalue]['counts']
        colortable = labeldict[itervalue]['colortable']
        head_tail = os.path.split(file)
        originfile, extension = os.path.splitext(head_tail[1])
        if len(path) > 0:
            tup = (labels, counts, colortable, [], file)
            _band, segimg, small_segimg = self.showcounting(tup, False, True, True, whext, blkext)
            imageband = segimg
            draw = ImageDraw.Draw(imageband)
            uniquelabels = list(colortable.keys())
            tempdict = {}
            pixelmmratio = 1.0
            print('pixelmmratio', pixelmmratio)
            if file not in self.kernersizes:
                for uni in uniquelabels:
                    if uni != 0:
                        pixelloc = np.where(labels == float(uni))
                        try:
                            ulx = min(pixelloc[1])
                        except:
                            continue
                        uly = min(pixelloc[0])
                        rlx = max(pixelloc[1])
                        rly = max(pixelloc[0])
                        print(ulx, uly, rlx, rly)
                        midx = ulx + int((rlx - ulx) / 2)
                        midy = uly + int((rly - uly) / 2)
                        length = {}
                        currborder = tkintercore.get_boundaryloc(labels, uni)
                        # print('currborder',currborder)
                        print('currborder length', len(currborder[0]) * len(currborder[1]))
                        pixperc = float(len(pixelloc[0]) / (labels.shape[0] * labels.shape[1]))
                        print('pix length percentage', pixperc)
                        if pixperc > 0.06:
                            x0 = ulx
                            y0 = uly
                            x1 = rlx
                            y1 = rly
                            kernellength = float(((x0 - x1) ** 2 + (y0 - y1) ** 2) ** 0.5)
                        else:
                            for i in range(len(currborder[0])):
                                for j in range(i + 1, len(currborder[0])):
                                    templength = float(((currborder[0][i] - currborder[0][j]) ** 2 + (
                                                currborder[1][i] - currborder[1][j]) ** 2) ** 0.5)
                                    length.update({(i, j): templength})
                            sortedlength = sorted(length, key=length.get, reverse=True)
                            try:
                                topcouple = sortedlength[0]
                            except:
                                continue
                            kernellength = length[topcouple]
                            i = topcouple[0]
                            j = topcouple[1]
                            x0 = currborder[1][i]
                            y0 = currborder[0][i]
                            x1 = currborder[1][j]
                            y1 = currborder[0][j]
                            # slope=float((y0-y1)/(x0-x1))
                            linepoints = [(currborder[1][i], currborder[0][i]), (currborder[1][j], currborder[0][j])]
                            # draw.line(linepoints,fill='yellow')
                            # points=linepixels(currborder[1][i],currborder[0][i],currborder[1][j],currborder[0][j])

                        lengthpoints = cal_kernelsize.bresenhamline(x0, y0, x1, y1)  # x0,y0,x1,y1
                        for point in lengthpoints:
                            # if imgtypevar.get()=='0':
                            draw.point([int(point[0]), int(point[1])], fill='yellow')
                        tengentaddpoints = cal_kernelsize.tengentadd(x0, y0, x1, y1, rlx, rly, labels,
                                                                     uni)  # find tangent line above
                        # for point in tengentaddpoints:
                        # if int(point[0])>=ulx and int(point[0])<=rlx and int(point[1])>=uly and int(point[1])<=rly:
                        #    draw.point([int(point[0]),int(point[1])],fill='green')
                        tengentsubpoints = cal_kernelsize.tengentsub(x0, y0, x1, y1, ulx, uly, labels,
                                                                     uni)  # find tangent line below
                        # for point in tengentsubpoints:
                        #    draw.point([int(point[0]),int(point[1])],fill='green')
                        pointmatchdict = {}
                        for i in range(len(tengentaddpoints)):  # find the pixel pair with shortest distance
                            width = kernellength
                            pointmatch = []
                            point = tengentaddpoints[i]
                            try:
                                templabel = labels[int(point[1]), int(point[0])]
                            except:
                                continue
                            if templabel == uni:
                                for j in range(len(tengentsubpoints)):
                                    subpoint = tengentsubpoints[j]
                                    tempwidth = float(
                                        ((point[0] - subpoint[0]) ** 2 + (point[1] - subpoint[1]) ** 2) ** 0.5)
                                    if tempwidth < width:
                                        pointmatch[:] = []
                                        pointmatch.append(point)
                                        pointmatch.append(subpoint)
                                        # print('tempwidth',width)
                                        width = tempwidth
                            if len(pointmatch) > 0:
                                # print('pointmatch',pointmatch)
                                pointmatchdict.update({(pointmatch[0], pointmatch[1]): width})
                        widthsort = sorted(pointmatchdict, key=pointmatchdict.get, reverse=True)
                        try:
                            pointmatch = widthsort[0]
                            print('final pointmatch', pointmatch)
                        except:
                            continue
                        if len(pointmatch) > 0:
                            x0 = int(pointmatch[0][0])
                            y0 = int(pointmatch[0][1])
                            x1 = int(pointmatch[1][0])
                            y1 = int(pointmatch[1][1])
                            # if imgtypevar.get()=='0':
                            draw.line([(x0, y0), (x1, y1)], fill='yellow')
                            width = float(((x0 - x1) ** 2 + (y0 - y1) ** 2) ** 0.5)
                            print('width', width, 'length', kernellength)
                            print('kernelwidth=' + str(width * pixelmmratio))
                            print('kernellength=' + str(kernellength * pixelmmratio))
                            # print('kernelwidth='+str(kernelwidth*pixelmmratio))
                            tempdict.update({uni: [kernellength, width, pixelmmratio ** 2 * len(pixelloc[0]),
                                                   kernellength * pixelmmratio, width * pixelmmratio]})
                        if uni in colortable:
                            canvastext = str(colortable[uni])
                        else:
                            canvastext = 'No label'
                        # if imgtypevar.get()=='0':
                        draw.text((midx - 1, midy + 1), text=canvastext, font=smallfont, fill='white')
                        draw.text((midx + 1, midy + 1), text=canvastext, font=smallfont, fill='white')
                        draw.text((midx - 1, midy - 1), text=canvastext, font=smallfont, fill='white')
                        draw.text((midx + 1, midy - 1), text=canvastext, font=smallfont, fill='white')
                        # draw.text((midx,midy),text=canvastext,font=font,fill=(141,2,31,0))
                        draw.text((midx, midy), text=canvastext, font=smallfont, fill='black')

                        # print(event.x, event.y, labels[event.x, event.y], ulx, uly, rlx, rly)

                        # recborder = canvas.create_rectangle(ulx, uly, rlx, rly, outline='red')
                        # drawcontents.append(recborder)
                self.kernersizes.update({file: tempdict})
            originheight, originwidth = self.batch_Multigraybands[file].size
            image = imageband.resize([originwidth, originheight], resample=Image.BILINEAR)
            extcolor = ""
            if whext == True:
                extcolor = "-extwht"
            if blkext == True:
                extcolor = "-extblk"
            image.save(path + '/' + originfile + extcolor + '-sizeresult' + '.png', "PNG")
            tup = (labels, counts, colortable, [], file)
            _band, segimg, small_segimg = self.showcounting(tup, False, True, True, whext, blkext)
            segimage = segimg.resize([originwidth, originheight], resample=Image.BILINEAR)
            segimage.save(path + '/' + originfile + extcolor + '-segmentresult' + '.png', "PNG")
            _band, segimg, small_segimg = self.showcounting(tup, True, True, True, whext, blkext)
            segimage = segimg.resize([originwidth, originheight], resample=Image.BILINEAR)
            segimage.save(path + '/' + originfile + extcolor + '-labelresult' + '.png', "PNG")

    def export_result(self):
        file = self.file
        if len(batch_filenames) == 0:
            print('No files', 'Please load images to process')
            return
        suggsize = 8
        smallfont = ImageFont.truetype('cmb10.ttf', size=suggsize)
        self.kernersizes = {}
        # path=filedialog.askdirectory()
        self.export_ext(True, False)
        self.export_ext(False, True)
        # for file in batch_filenames:
        labeldict = self.batch_results[self.file][0]
        itervalue = 'iter0'
        labels = labeldict[itervalue]['labels']
        counts = labeldict[itervalue]['counts']
        colortable = labeldict[itervalue]['colortable']
        head_tail = os.path.split(self.file)
        originfile, extension = os.path.splitext(head_tail[1])
        uniquelabels = list(colortable.keys())
        originheight, originwidth = self.batch_Multigraybands[file].size
        ratio = int(batch_findratio([512, 512], [labels.shape[0], labels.shape[1]]))
        if labels.shape[0] < 512:
            cache = (
            np.zeros((labels.shape[0] * ratio, labels.shape[1] * ratio)), {"f": int(ratio), "stride": int(ratio)})
            convband = tkintercorestat.pool_backward(labels, cache)
        else:
            if labels.shape[0] > 512:
                convband = cv2.resize(labels, (512, 512), interpolation=cv2.INTER_LINEAR)
            else:
                if labels.shape[0] == 512:
                    convband = np.copy(labels)

        '''export pixel loc'''
        locfilename = self.exportpath + '/' + originfile + '-pixellocs.csv'
        with open(locfilename, mode='w') as f:
            csvwriter = csv.writer(f)
            rowcontent = ['id', 'locs']
            csvwriter.writerow(rowcontent)
            for uni in uniquelabels:
                if uni != 0:
                    tempuni = colortable[uni]
                    if tempuni == 'Ref':
                        pixelloc = np.where(convband == 65535)
                    else:
                        pixelloc = np.where(convband == float(uni))
                    rowcontent = [colortable[uni]]
                    rowcontent = rowcontent + list(pixelloc[0])
                    csvwriter.writerow(rowcontent)
                    rowcontent = [colortable[uni]]
                    rowcontent = rowcontent + list(pixelloc[1])
                    csvwriter.writerow(rowcontent)

            f.close()

        if len(self.exportpath) > 0:
            tup = (labels, counts, colortable, [], self.file)
            _band, segimg, small_segimg = self.showcounting(tup, False)
            # imageband=outputimgbands[file][itervalue]
            imageband = segimg
            # draw=ImageDraw.Draw(imageband)
            uniquelabels = list(colortable.keys())
            # tempdict={}
            pixelmmratio = 1.0
            # print('coinsize',coinsize.get(),'pixelmmratio',pixelmmratio)
            print('pixelmmratio', pixelmmratio)
            originheight, originwidth = self.batch_Multigraybands[file].size
        image = imageband.resize([originwidth, originheight], resample=Image.BILINEAR)
        image.save(self.exportpath + '/' + originfile + '-sizeresult' + '.png', "PNG")
        tup = (labels, counts, colortable, [], file)
        _band, segimg, small_segimg = self.showcounting(tup, False)
        segimage = segimg.resize([originwidth, originheight], resample=Image.BILINEAR)
        segimage.save(self.exportpath + '/' + originfile + '-segmentresult' + '.png', "PNG")
        _band, segimg, small_segimg = self.showcounting(tup, True)
        segimage = segimg.resize([originwidth, originheight], resample=Image.BILINEAR)
        segimage.save(self.exportpath + '/' + originfile + '-labelresult' + '.png', "PNG")
        originrestoredband = np.copy(labels)
        restoredband = originrestoredband.astype('uint8')
        colordicesband = self.batch_colordicesband[file]
        colordiv = np.zeros((colordicesband.shape[0], colordicesband.shape[1], 3))
        self.savePCAimg(originfile)

        # kvar=int(kmeans.get())
        # print('kvar',kvar)
        # for i in range(kvar):
        #     locs=np.where(colordicesband==i)
        #     colordiv[locs]=colorbandtable[i]
        # colordivimg=Image.fromarray(colordiv.astype('uint8'))
        # colordivimg.save(path+'/'+originfile+'-colordevice'+'.jpeg',"JPEG")
        colordivimg = Image.open(file + '-allcolorindex.png')
        copycolordiv = colordivimg.resize([originwidth, originheight], resample=Image.BILINEAR)
        copycolordiv.save(self.exportpath + '/' + originfile + '-colordevice' + '.png', "PNG")
        # pyplt.imsave(path+'/'+originfile+'-colordevice'+'.png',colordiv.astype('uint8'))
        # copybinary=np.zeros((originbinaryimg.shape[0],originbinaryimg.shape[1],3),dtype='float')
        # nonzeros=np.where(originbinaryimg==1)
        # copybinary[nonzeros]=[255,255,0]
        # binaryimg=Image.fromarray(copybinary.astype('uint8'))
        binaryimg = Image.open(file + '-binaryimg.png')
        copybinaryimg = binaryimg.resize([originwidth, originheight], resample=Image.BILINEAR)
        copybinaryimg.save(self.exportpath + '/' + originfile + '-binaryimg' + '.png', "PNG")
        # pyplt.imsave(path+'/'+originfile+'-binaryimg'+'.png',originbinaryimg.astype('uint8'))

        # restoredband=cv2.resize(src=restoredband,dsize=(originwidth,originheight),interpolation=cv2.INTER_LINEAR)
        print(restoredband.shape)
        currentsizes = self.kernersizes[self.file]
        indicekeys = list(self.batch_originbandarray[self.file].keys())
        indeclist = [0 for i in range(len(indicekeys) * 3)]
        pcalist = [0 for i in range(3)]
        # temppcabands=np.zeros((self.batch_originpcabands[self.file].shape[0],len(pcs)))
        # for i in range(len(pcs)):
        #     temppcabands[:,i]=temppcabands[:,i]+self.batch_originpcabands[self.file][:,pcs[i]-1]
        # pcabands=np.mean(temppcabands,axis=1)
        # # pcabands=pcabands.reshape((originheight,originwidth))
        # pcabands=pcabands.reshape((self.displayfea_l,self.displayfea_w))
        pcabands = np.copy(self.displaypclagels)
        datatable = {}
        origindata = {}
        for key in indicekeys:
            data = self.batch_originbandarray[self.file][key]
            data = data.tolist()
            tempdict = {key: data}
            origindata.update(tempdict)
            print(key)
        # for uni in colortable:
        print(uniquelabels)
        print('len uniquelabels', len(uniquelabels))
        for uni in uniquelabels:
            print(uni, colortable[uni])
            uniloc = np.where(labels == float(uni))
            if len(uniloc) == 0 or len(uniloc[1]) == 0:
                print('no uniloc\n')
                print(uniloc[0], uniloc[1])
                continue
            smalluniloc = np.where(originrestoredband == uni)
            ulx, uly = min(smalluniloc[1]), min(smalluniloc[0])
            rlx, rly = max(smalluniloc[1]), max(smalluniloc[0])
            width = rlx - ulx
            length = rly - uly
            print(width, length)
            subarea = restoredband[uly:rly + 1, ulx:rlx + 1]
            subarea = subarea.tolist()
            amount = len(uniloc[0])
            print(amount)
            try:
                sizes = currentsizes[uni]
            except:
                print('no sizes\n')
                continue
            # templist=[amount,length,width]
            templist = [amount, sizes[0], sizes[1], sizes[2], sizes[3], sizes[4]]
            tempdict = {colortable[uni]: templist + indeclist + pcalist}  # NIR,Redeyes,R,G,B,NDVI,area
            print(tempdict)
            for ki in range(len(indicekeys)):
                originNDVI = origindata[indicekeys[ki]]
                print(len(originNDVI), len(originNDVI[0]))
                pixellist = []
                for k in range(len(uniloc[0])):
                    # print(uniloc[0][k],uniloc[1][k])
                    try:
                        tempdict[colortable[uni]][6 + ki * 3] += originNDVI[uniloc[0][k]][uniloc[1][k]]
                    except IndexError:
                        print(uniloc[0][k], uniloc[1][k])
                    tempdict[colortable[uni]][7 + ki * 3] += originNDVI[uniloc[0][k]][uniloc[1][k]]
                    pixellist.append(originNDVI[uniloc[0][k]][uniloc[1][k]])
                tempdict[colortable[uni]][ki * 3 + 6] = tempdict[colortable[uni]][ki * 3 + 6] / amount
                tempdict[colortable[uni]][ki * 3 + 8] = np.std(pixellist)
            pixellist = []
            for k in range(len(uniloc[0])):
                try:
                    tempdict[colortable[uni]][-2] += pcabands[uniloc[0][k]][uniloc[1][k]]
                except IndexError:
                    print(uniloc[0][k], uniloc[1][k])
                tempdict[colortable[uni]][-3] += pcabands[uniloc[0][k]][uniloc[1][k]]
                pixellist.append(pcabands[uniloc[0][k]][uniloc[1][k]])
                tempdict[colortable[uni]][-3] = tempdict[colortable[uni]][-3] / amount
                tempdict[colortable[uni]][-1] = np.std(pixellist)
            datatable.update(tempdict)
        filename = self.exportpath + '/' + originfile + '-outputdata.csv'
        with open(filename, mode='w') as f:
            csvwriter = csv.writer(f)
            rowcontent = ['Index', 'Plot', 'Area(#pixel)', 'Length(#pixel)', 'Width(#pixel)', 'Area(mm2)', 'Length(mm)',
                          'Width(mm)']
            for key in indicekeys:
                rowcontent.append('avg-' + str(key))
                rowcontent.append('sum-' + str(key))
                rowcontent.append('std-' + str(key))
            rowcontent.append('avg-PCA')
            rowcontent.append('sum-PCA')
            rowcontent.append('std-PCA')
            # csvwriter.writerow(['ID','NIR','Red Edge','Red','Green','Blue','NIRv.s.Green','LabOstu','area(#of pixel)'])
            # csvwriter.writerow(['Index','Plot','Area(#pixels)','avg-NDVI','sum-NDVI','std-NDVI','Length(#pixel)','Width(#pixel)'])#,'#holes'])
            csvwriter.writerow(rowcontent)
            i = 1
            for uni in datatable:
                row = [i, uni]
                for j in range(len(datatable[uni])):
                    row.append(datatable[uni][j])
                # row=[i,uni,datatable[uni][0],datatable[uni][1],datatable[uni][2],datatable[uni][5],datatable[uni][3],datatable[uni][4]]#,
                # datatable[uni][5]]
                i += 1
                print(row)
                csvwriter.writerow(row)
        print('total data length=', len(datatable))

    def process(self):
        if self.Open_batchimage() == False:
            return
        self.singleband()
        colordicesband = self.kmeansclassify()
        if type(colordicesband) == type(None):
            return
        self.batch_colordicesband.update({self.file: colordicesband})
        currentlabels, originbinaryimg = self.generateimgplant(colordicesband)
        if self.extraction(currentlabels) == False:
            return
        if self.resegment() == False:
            return
        self.export_result()


def batch_process():
    global batch_colordicesband
    global batch_Multiimage, batch_Multigray, batch_Multitype, batch_Multiimagebands, batch_Multigraybands
    global batch_displaybandarray, batch_originbandarray, batch_originpcabands
    global batch_results

    if len(batch_filenames) == 0:
        print('No files', 'Please load images to process')
        return
    cpunum = multiprocessing.cpu_count()
    print('# of CPUs', cpunum)
    starttime = time.time()
    print('start time', starttime)
    for file in batch_filenames:
        procobj = batch_ser_func(file)
        procobj.process()
        del procobj
    print('used time', time.time() - starttime)

    print('Done', 'Batch process ends!')



def testPreview():
    if (camera.isconnec):
        if camera.isplay:
            if not camera.ispreview:
                camera.ispreview = True
                try:
                    camera_file = gp.check_result(gp.gp_camera_capture_preview(camera.camera))
                    file_data = gp.check_result(gp.gp_file_get_data_and_size(camera_file))
                    image = Image.open(io.BytesIO(file_data))
                    image = ImageTk.PhotoImage(image)
                    panel.configure(image=image)
                    panel.image = image
                    panel.pack(side="top", fill="both", expand="yes")


                except Exception as e:
                    print("Frame Read error")
                camera.ispreview = False
        elif camera.is_capture_image:
            camera.is_capture_image = False
            # self.pixmap = self.PILimageToQImage(self.capture_image)
            # self.imageLabel.setPixmap(self.pixmap)
            image = Image.open("tempcapture/capt0000.jpg")
            imageResize = image.resize((960, 640), Image.ANTIALIAS)
            imageResize = ImageTk.PhotoImage(imageResize)
            panel.configure(image=imageResize)
            panel.image = imageResize
            panel.pack(side="top", fill="both", expand="yes")
        elif camera.is_load_image:
            camera.is_load_image = False
            imageResize = camera.imageView.resize((960, 640), Image.ANTIALIAS)
            #
            # # Creating object of PhotoImage() class to display the frame
            imageDisplay = ImageTk.PhotoImage(imageResize)
            #
            # # Configuring the label to display the frame
            panel.config(image=imageDisplay)
            #
            # # Keeping a reference
            panel.photo = imageDisplay
            panel.pack(side="top", fill="both", expand="yes")
    elif camera.is_load_image == False:
        img = ImageTk.PhotoImage(Image.open("nocam.jpg"))
        panel.configure(image=img)
        panel.image = img
        panel.pack(side="top", fill="both", expand="yes")
    else:

            # camera.is_load_image = False
            imageResize = camera.imageView.resize((960, 640), Image.ANTIALIAS)
            #
            # # Creating object of PhotoImage() class to display the frame
            imageDisplay = ImageTk.PhotoImage(imageResize)
            #
            # # Configuring the label to display the frame
            panel.config(image=imageDisplay)
            #
            # # Keeping a reference
            panel.photo = imageDisplay
            panel.pack(side="top", fill="both", expand="yes")

    panel.after(10, testPreview)

def startCapture():
    pause_()
    camera.exit_camera()
    print(camera.isconnec)

    OK, path = camera.capture_image()

    if OK:
        camera.image_capture = Image.open(path)
        camera.image_capture.show()
        camera.is_capture_image = True

    else:
        camera.showMesage("Capture Fail..", "..")



def play_pause():
    if camera.isplay:
        pause_()
    else:
        play_()

def pause_():
    camera.isplay = False

def play_():
    camera.isplay = True

def process():
    Open_batchfile()
    Open_batchfolder()
    batch_process()
    camera.output_image = Image.open("test/output/test-extwht-sizeresult.png")
    camera.output_image.show()
def loadImages():
    pause_()
    # Presenting user with a pop-up for directory selection. initialdir argument is optional
    # Retrieving the user-input destination directory and storing it in destinationDirectory
    # Setting the initialdir argument is optional. SET IT TO YOUR DIRECTORY PATH
    openDirectory = filedialog.askopenfilename(initialdir="YOUR DIRECTORY PATH")

    # Displaying the directory in the directory textbox
    # root.imagePath.set(openDirectory)

    # Opening the saved image using the open() of Image class which takes the saved image as the argument
    camera.imageView = Image.open(openDirectory)
    camera.is_load_image = True
    # Resizing the image using Image.resize()
    # imageResize = imageView.resize((960, 640), Image.ANTIALIAS)
    #
    # # Creating object of PhotoImage() class to display the frame
    # imageDisplay = ImageTk.PhotoImage(imageResize)
    #
    # # Configuring the label to display the frame
    # panel.config(image=imageDisplay)
    #
    # # Keeping a reference
    # panel.photo = imageDisplay

    """
    Creates a panel and starts the framereader
    """


def exportResult():
    pass

root = ttk.Window(themename="flatly")
root.title("SeedCounter")
root.geometry("1400x700")
root.resizable(True, True)
root.configure(background="sky blue")

# root.columnconfigure(0, weight = 4)
# root.columnconfigure(1, weight = 1)
# root.rowconfigure(0, weight = 1)
#
# col1 = ttk.Frame(padding = 10)
# col1.grid(row = 0, column = 0, sticky = NSEW)
#
# col2 = ttk.Frame(padding = 10)
# col2.grid(row = 0, column = 1, sticky = NSEW)
#
# # device info
# view_info = ttk.Labelframe(col1, text='Camera View', padding=10)
# view_info.pack(side=TOP, fill=BOTH, expand=YES)
#
# control_info = ttk.Labelframe(col2, text='Control Panel', padding=10)
# control_info.pack(side=TOP, fill=BOTH, expand=YES)
# # testPreview()
# #
panel = ttk.Label(view_info)
img = ImageTk.PhotoImage(Image.open("nocam.jpg"))
panel.configure(image=img)
panel.image = img
panel.pack(fill = X)
#
# live_button = ttk.Button(
#             master = col1,
#             text="LIVE",
#             command=play_pause,
#             bootstyle=SUCCESS,
#             width=10,
#         )
#
#
# live_button.pack(side=BOTTOM, padx=5, pady = 5)
# live_button.focus_set()
LiveButton = ttk.Button(root, width=10, text="LIVE",  bootstyle=SUCCESS, command=play_pause)
LiveButton.pack(side = 'bottom')

captureButton = tk.Button(root, width=10, text="CAPTURE", command=startCapture)
captureButton.pack(side = 'right')
loadButton = tk.Button(root, width=10, text="LOAD", command=loadImages)
loadButton.pack(side = 'right')
processButton = tk.Button(root, width=10, text="PROCESS", command=process)
processButton.pack(side = 'right')



exportButton = tk.Button(root, width=10, text="EXPORT", command=exportResult)
exportButton.pack(side = 'right')

root.mainloop()
