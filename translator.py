#coding=utf8
from PIL import ImageGrab
import pygetwindow as gw
import Tkinter as tk
from Tkinter import StringVar

from time import sleep
import threading

from PIL import Image
import sys
import pyocr
import pyocr.builders
import re

import urllib2
import urllib
import requests
import json
import js2py

def GetJs():
    with open(r'sign.js') as f:
        return f.read()

def GetSign(content):
    run_js = js2py.EvalJs({})
    run_js.execute(GetJs())
    return run_js.e(content)

def to_utf8(text):
    if isinstance(text, unicode):
        # unicode to utf-8
        return text.encode('utf-8')
    try:
        # maybe utf-8
        return text.decode('utf-8').encode('utf-8')
    except UnicodeError:
        # gbk to utf-8
        return text.decode('gbk').encode('utf-8')

class BaiDuTranslateAPI(object):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'
    }
    def __init__(self):
        super(BaiDuTranslateAPI,self).__init__()
        self.GetReady()
    def GetReady(self):
        url_index = 'https://www.baidu.com'
        self.session = requests.session()
        self.session.get(url=url_index, headers=self.headers)
        self.headers['Referer'] = url_index
        url_html = 'https://fanyi.baidu.com/translate?aldtype=16047&query=&keyfrom=baidu&smartresult=dict&lang=auto2zh'
        html = self.session.get(url=url_html, headers=self.headers)
        comm = re.compile('token: \'(\w+)\'')
        self.token = comm.search(html.text).group(1)
        self.headers['Referer'] = url_html

    def Get_Js(self):
        with open(r'sign.js') as f:
            return f.read()

    def BaiDu(self,file):
        run_js = js2py.EvalJs({})
        run_js.execute(self.Get_Js())
        sign = run_js.e(file)
        url_api = 'https://fanyi.baidu.com/v2transapi'
        is_it = file

        langdetect_url = "https://fanyi.baidu.com/langdetect"
        langdetect_data = {"query":file}
        landetectHTML = self.session.post(url=langdetect_url, headers=self.headers, data=langdetect_data).json()
        lan = landetectHTML['lan']

        if is_it and lan == 'zh':
            iia = 'zh'
            iib = 'jp'
        else:
            iia = lan
            iib = 'zh'
        data = {
            'from': iia,
            'to': iib,
            'query': file,
            'transtype': 'realtime',
            'simple_means_flag': '3',
            'sign': sign,
            'token': self.token
        }
        html = self.session.post(url=url_api, headers=self.headers, data=data).json()
        print("--- Posting to Baidu ---")
        return (html['trans_result']['data'][0]['dst'])
    def Translate(self,file='i'):
        # self.zhunbei()
        files = self.BaiDu(file)
        return files

class Window(tk.Toplevel):     
    def __init__(self, master):
        tk.Toplevel.__init__(self)
        self.title("Window")

class Rect():
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

class CropData():
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

def GetCaptureArea():
    global window
    global root
    global canvas
    global cropRect
    captureWindow = gw.getWindowsWithTitle(u'选择范围')
    if (len(captureWindow) == 0):
        window = Window(root)
        window.title(u"选择范围")
        window.wm_attributes("-topmost", True)
        window.wm_attributes("-alpha", 0.5)
        window.wm_attributes("-fullscreen", True)
        window.overrideredirect(True)
        canvas = tk.Canvas(window, cursor="cross", bg='black', highlightthickness=0, bd=0)
        canvas.pack(fill=tk.BOTH, expand=tk.YES)
        canvas.bind("<ButtonPress-1>", SetCropStartPos)
        canvas.bind("<Motion>", UpdateCropArea)
        canvas.bind("<ButtonRelease-1>", SetCropEndPos)

def SetCropStartPos(event):
    global canvas
    global mouseEventStart
    global cropRect
    mouseEventStart = True
    cropData.x1 = event.x
    cropData.y1 = event.y
    cropRect = canvas.create_rectangle(cropData.x1, cropData.y1, cropData.x1, cropData.y1, fill='white')

def UpdateCropArea(event):
    global mouseEventStart
    if (mouseEventStart == False):
        return

    global canvas
    global cropRect
    cropData.x2 = event.x
    cropData.y2 = event.y
    canvas.coords(cropRect, cropData.x1, cropData.y1, cropData.x2, cropData.y2)

def SetCropEndPos(event):
    global mouseEventStart
    if (mouseEventStart == False):
        return

    global canvas
    global window
    global cropRect
    cropData.x2 = event.x
    cropData.y2 = event.y
    canvas.coords(cropRect, cropData.x1, cropData.y1, cropData.x2, cropData.y2)

    window.destroy()
    mouseEventStart = False

def Translate():
    CropPic()
    DoOcr()


def CropPic():
    global cropData, translatedText
    print(cropData.x1,cropData.y1,cropData.x2,cropData.y2)
    pic = ImageGrab.grab((cropData.x1, cropData.y1, cropData.x2, cropData.y2))
    pic.save(r'translate.jpg')
    

def DoOcr():
    global translator
    tools = pyocr.get_available_tools()
    tool = tools[0]
    langs = tool.get_available_languages()
    print("Available languages: %s" % ", ".join(langs))
    res = tool.image_to_string(Image.open("./translate.jpg"), lang= "jpn+eng+osd", builder=pyocr.builders.TextBuilder(tesseract_layout=6))
    res = re.sub('([あ-んア-ン一-龥ー])\s+((?=[あ-んア-ン一-龥ー]))',
      r'\1\2', res)
    res = re.sub(r'\s+', '', res)
    trans = translator.Translate(res)
    ChangeText(u"【原文】\n%s \n【译文】\n%s" % (res, trans))

def ChangeText(text):
    global resultText
    resultText.configure(state='normal')
    resultText.delete("1.0", "end")
    resultText.insert('end', text)
    resultText.configure(state='disabled')

mouseEventStart = False
canvas = None
cropRect = None
window = None
translator = BaiDuTranslateAPI()
cropData = CropData(0,0,0,0)
root = tk.Tk()
root.title(u"踢踢的二次元小翻译")
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
width = 320
height = 320
size = '%dx%d+%d+%d' % (width, height, (screen_width - width)/2, (screen_height - height)/2)


root.wm_attributes("-topmost", True)
root.geometry(size) 

selectAreaBtn = tk.Button(root, text="选择翻译文本范围", width=60, command=GetCaptureArea)
selectAreaBtn.pack()

translateBtn = tk.Button(root, text="开始翻译", width=60, command=Translate)
translateBtn.pack()

tk.Label(root, text="翻译结果：").pack()

resultText = tk.Text(root,state = "disabled", font=(20))
resultText.pack(fill=tk.BOTH, expand=tk.YES)

root.mainloop()

