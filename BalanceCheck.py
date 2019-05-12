# -*- coding: utf-8 -*-
"""
Created on Sun May 12 04:57:36 2019

@author: Noko
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import pickle
import os

class WebCache:
    def __init__(self, session, expirationTime, filename=""):
        self.pages = {}
        self.session = session
        self.filename = filename
        if self.filename != "" and os.path.exists(filename):
            with open(self.filename, "rb") as file:
                self.pages = pickle.load(file)
    
    def save(self):
        if self.filename != "":
            with open(self.filename, "wb") as file:
                pickle.dump(self.pages, file)
    
    def get(self, url):
        if not url in self.pages:
            self.pages[url] = self.session.get(url)
        return self.pages[url]
    
    def clear(self):
        self.pages = {}
        
    def post(self, url, params):
        lookup = url + json.dumps(params)
        if not lookup in self.pages:
            self.pages[lookup] = self.session.post(url, params)
        return self.pages[lookup]
    

class WebAfricaUsageRequest:
    def __init__(self, Session):
        self.urls = {
                "home": "https://www.webafrica.co.za/clientarea.php",
                "login": "https://www.webafrica.co.za/dologin.php",
                "products": "https://www.webafrica.co.za/myservices.php?pagetype=adsl",
                "product": "https://www.webafrica.co.za/clientarea.php?action=productdetails&{productId}&modop=custom&a=LoginToDSLConsole",
                "fibre": "https://www.webafrica.co.za/includes/fup.handler.php",
        }
        self.session = Session
                
    def Login(self, username, password):
        self.session.clear()
        home = self.session.get(self.urls["home"])
        #get login token
        soup = BeautifulSoup(home.text, features="html.parser")
        token = soup.find('input', {'name': 'token'})
        if token != None:
            token = token.get('value')
        else:
            raise AttributeError("Home page does not contain login token")
        #login to website
        self.session.post(self.urls["login"], {
                "token": token,
                "username": username,
                "password": password,
                "rememberme": "on",
        })
            
    def GetProductIds(self):
        products = self.session.get(self.urls["products"])
        soup = BeautifulSoup(products.text, features="html.parser")
        ids = {}
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and href.find('LoginToDSLConsole') != -1:
                result = re.findall(r'id=\d+', href)
                if len(result) == 1:
                    ids[result[0]] = True
        return list(ids.keys())
    
    def GetProduct(self, productId):
        page = self.session.get(self.urls['product'].format(productId=productId))
        soup = BeautifulSoup(page.text, features="html.parser")
        results = {"id": productId[3:]}
        lastUpdate = soup.find('span', {'id': 'ctl00_ctl00_contentDefault_contentControlPanel_lbllastUpdted'})
        if lastUpdate:
            results["lastUpdate"] = lastUpdate.text
        lteUsage = soup.find('span', {'id': 'ctl00_ctl00_contentDefault_contentControlPanel_lblAnytimeCap'})
        if lteUsage and lteUsage.text != '':
            results["lteUsage"] = lteUsage.text
        else:
            username = soup.find('input', {'data-role': 'userName'}).get('value')
            response = self.session.post(self.urls["fibre"], {
                    "cmd": "getfupinfo",
                    "username": username,
            })
            response = json.loads(response.text)
            usage = response['Data']['Usage'] / 1024 / 1024 / 1024
            total = response['Data']['Threshold'] / 1024 / 1024 / 1024
            results["fibreUsage"] = "({:.2f} GB of {:.2f} GB)".format(usage, total)
        return results
    
        

if __name__ == "__main__":
    username = ""
    password = ""
    
    with open("config.json") as file:
        params = json.load(file)
        username = params['username']
        password = params['password']

    Cache = WebCache(requests.Session(), None, 'Cache.obj')
    
    webAfrica = WebAfricaUsageRequest(Cache)
    if not os.path.exists('Cache.obj'):
        webAfrica.Login(username, password)
    ids = webAfrica.GetProductIds()
    pages = []
    for productId in ids:
        pages.append(webAfrica.GetProduct(productId))
    print(pages)
    
    Cache.save()