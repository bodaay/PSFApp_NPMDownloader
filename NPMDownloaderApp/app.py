import os
import sys
import sqlite3
import requests
import shutil
import hashlib
import json
import time
import signal
import base64
from datetime import datetime
# I'm using thead pool, because its easier and I can use global variables easily with it, We don't need high processing power for this project, just multi thread
from multiprocessing.pool import ThreadPool
from termcolor import colored
import tqdm  # pip3 install tqdm
import re

MaxDownloadTaks = 50
ForceReDownloadCatalogItems = False
DATA_FOLDER_NAME = "/Synology/NuGet/"
NuGet_Main_Json_Index_Link = "https://api.nuget.org/v3/catalog0/index.json"
NuGet_Main_Packages_Path = "https://www.nuget.org/api/v2/package/"
working_path = DATA_FOLDER_NAME
packages_path = os.path.join(DATA_FOLDER_NAME, "packages")
packages_data_path = os.path.join(DATA_FOLDER_NAME, "data")

logFileName = datetime.now().strftime('FailedList_%d-%m-%Y_%H_%M.log')


def GetMD5(file1):
    if not os.path.exists(file1):
        return None
    hashed = hashlib.md5()
    with open(file1, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hashed.update(chunk)
    return hashed.hexdigest()


def GetSHA512(file1):
    if not os.path.exists(file1):
        return None
    hashed = hashlib.sha512()
    with open(file1, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hashed.update(chunk)
    return hashed.hexdigest()


def GetSHA256(file1):
    if not os.path.exists(file1):
        return None
    hashed = hashlib.sha256()
    with open(file1, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hashed.update(chunk)
    return hashed.hexdigest()


def ChechHash(hashfunction, file):
    if hashfunction.lower() == "sha512":
        return GetSHA512(file)
    if hashfunction.lower() == "sha256":
        return GetSHA512(file)
    if hashfunction.lower() == "md5":
        return GetSHA512(file)


def FilesMatching(file1, file2):
    # first we check by size, faster
    if not os.path.exists(file1):
        return False
    if not os.path.exists(file2):
        return False
    if os.stat(file1).st_size != os.stat(file2).st_size:
        return False
    if GetMD5(file1) != GetMD5(file2):
        return False
    # then we check by checksum
    return True


def start(argv):
    # I want to get the path of app.py
    #base_path = os.path.dirname(os.path.realpath(__file__))

    if not os.path.exists(working_path):
        os.makedirs(working_path, exist_ok=True)
    if not os.path.exists(packages_path):
        os.makedirs(packages_path, exist_ok=True)
    if not os.path.exists(packages_data_path):
        os.makedirs(packages_data_path, exist_ok=True)
    local_temp_file_name = os.path.join(working_path, "index.temp.json")
    r = requests.get(NuGet_Main_Json_Index_Link, timeout=10)
    with open(local_temp_file_name, 'wb') as f:
        # shutil.copyfileobj(r.content, f) # this method you can use it if request.get is used with stream=true and writing r.raw
        f.write(r.content)
    original_file_name = os.path.join(working_path, "index.json")
    if FilesMatching(original_file_name, local_temp_file_name):
        print("No update happened since last download, aborting...")
        # return # Uncomment this later

    # make index.temp.json as index.json
    os.rename(local_temp_file_name, original_file_name)
    process_update(original_file_name)
    # # delete index.temp.json

    # os.remove(local_temp_file_name)
    return
    # installRequired.CheckRequiredModuels(required_modules)

# https://www.nuget.org/api/v2/package/vlc/1.1.8


# lock = Lock()

CatalogJsonFilesToProcess = []


def SaveAdnAppendToErrorLog(data):
    # timeS = datetime.now().strftime('FailedList__%H_%M_%d_%m_%Y.log.json')
    with open(logFileName, "a+") as outfile:
        outfile.write(data)


def signal_handler(sig, frame):
    print('\nYou pressed Ctrl+C!')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def processCatalogPageItem(item):
    downloadURL = ""
    try:
        foldername = item['@id'].rsplit('/', 2)[-2]
        fileName = item['@id'].rsplit('/', 1)[-1]
        fullFileNameWithPath = os.path.join(
            packages_data_path, foldername, fileName)
        # fullFileNameWithPath_temp = os.path.join(
        #     packages_data_path, foldername, fileName + ".temp")
        # if not os.path.exists(fullFileNameWithPath):
        os.makedirs(os.path.join(packages_data_path,
                                 foldername), exist_ok=True)
        r = requests.get(item['@id'], timeout=10)
        with open(fullFileNameWithPath, 'wb') as f:
            f.write(r.content)
        # lets load this json file
        with open(fullFileNameWithPath, 'r') as jsonfile:
            jsonObj = json.loads(jsonfile.read())
            # now we download the actual package
            packgeName = item['nuget:id']
            packgeVersion = item['nuget:version']
            packageDownloadPath = os.path.join(
                packages_path, packgeName, packgeVersion)
            downloadURL = NuGet_Main_Packages_Path + packgeName + "/" + packgeVersion
            packageDownloadFileName = packgeName.lower(
            ) + "." + packgeVersion.lower() + ".nupkg"
            packageDownloadFileName_WithPath = os.path.join(
                packageDownloadPath, packageDownloadFileName)
            os.makedirs(packageDownloadPath, exist_ok=True)
            r = requests.get(downloadURL, timeout=10)
            with open(packageDownloadFileName_WithPath, 'wb') as f:
                f.write(r.content)
                # I've canceled the below, since too many packages have their hash wrong in their JSON file !!! stupid microsoft piece of shit

                # # we have to verify the hash of the file
                # fileHash = base64.b64decode(jsonObj['packageHash']).hex()
                # fileHashAlgo = jsonObj['packageHashAlgorithm']
                # calculatedHash = ChechHash(
                #     fileHashAlgo, packageDownloadFileName_WithPath)
                # if not calculatedHash == fileHash:
                #     a = packageDownloadFileName_WithPath + "\n"
                #     b = jsonObj['packageHash'] + "\n"
                #     c = "Actual Hash: %s\n" % fileHash
                #     d = "Calculated Hash: %s\n" % calculatedHash
                #     z = a+b+c+d
                #     raise Exception('Hash Mismatch\n' + z)
            # os.rename(fullFileNameWithPath_temp, fullFileNameWithPath)

    except Exception as ex:
        raise Exception("%s\n%s\n%s" % (item['@id'], downloadURL, ex))


def DownloadAndProcessesItemJob(itemObj):
    global CatalogJsonFilesToProcess
    fname = itemObj['@id'].rsplit('/', 1)[-1]
    original_file_name = os.path.join(DATA_FOLDER_NAME, fname)
    local_download_file_name = os.path.join(
        DATA_FOLDER_NAME, fname + ".download")
    local_temp_file_name = os.path.join(
        DATA_FOLDER_NAME, fname + ".temp")
    # we will only download the index file, if .json and .temp both not available, this will he us avoid redownloading finished .temp files
    if (not os.path.exists(original_file_name) and not os.path.exists(local_temp_file_name)) or ForceReDownloadCatalogItems:
        r = requests.get(itemObj['@id'], timeout=10)
        with open(local_download_file_name, 'wb') as f:
            # shutil.copyfileobj(r.content, f) # this method you can use it if request.get is used with stream=true and writing r.raw
            f.write(r.content)
        os.rename(local_download_file_name, local_temp_file_name)
    # if .temp file exists, means this file has to be appened for downlaoding its files in the next process
    if os.path.exists(local_temp_file_name):
        # append temp name and original name
        CatalogJsonFilesToProcess.append(
            [local_temp_file_name, original_file_name])


def process_update(json_file):
    global CatalogJsonFilesToProcess
    with open(json_file, 'r') as jsonfile:
        jsonObj = json.loads(jsonfile.read())
        # pbar = ProgressBar(maxval=len(jsonObj['items']))
        print("Downloading Catalogs...")
        pool = ThreadPool(processes=MaxDownloadTaks)
        # got the below from: https://stackoverflow.com/questions/41920124/multiprocessing-use-tqdm-to-display-a-progress-bar/45276885
        list(tqdm.tqdm(pool.imap(DownloadAndProcessesItemJob,
                                 jsonObj['items']), total=len(jsonObj['items']), ))
        pool.close()
        pool.join()
        print("Processing New Catalog Pacakges...")
        index = 0
        jsonObj = None
        for cat_temp_name, cat_ori_name in CatalogJsonFilesToProcess:
            try:
                print("Processing Catalog (%s), %d/%d Finished" %
                      (cat_temp_name, index, len(CatalogJsonFilesToProcess)))
                with open(cat_temp_name, 'r') as jsonfile:
                    jsonObj = json.loads(jsonfile.read())
                    catalogpool = ThreadPool(processes=MaxDownloadTaks)
                    list(tqdm.tqdm(catalogpool.imap(processCatalogPageItem,
                                                    jsonObj['items']), total=len(jsonObj['items']), ))
                    # Now we can say we can change this Catalog file name, and remove the .temp since its already processed

                    os.rename(cat_temp_name, cat_ori_name)
                    catalogpool.close()
                    catalogpool.join()
            except Exception as ex:
                print(ex)
                ErrorLog = "****\nError in File: %s\n%s\n" % (cat_ori_name, ex)
                SaveAdnAppendToErrorLog(ErrorLog)
            finally:
                index += 1
