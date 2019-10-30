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
import codecs
import math
import urllib.parse
import numpy as np # pip3 install numpy
from datetime import datetime
# I'm using thead pool, because its easier and I can use global variables easily with it, We don't need high processing power for this project, just multi thread
from multiprocessing.pool import Pool
from termcolor import colored
from zipfile import ZipFile
import tqdm  # pip3 install tqdm
import re
 
#TODO: we should keep downloading _changes.json weekly, and host this somewhere else. I cannot download it myself. I'm thinking of create a lambda function on aws and hosting the file on aws s3, I'll do this later, too lazy to do it now

BatchSize = 40
MaxDownloadProcess = 40
MaxNumberOfDownloadRetries = 2
ROOT_FOLDER_NAME = "/Synology/NPM/"
SkimDB_Main_Registry_Link = "https://skimdb.npmjs.com/registry/"
working_path = os.path.join(ROOT_FOLDER_NAME,"sync_data_indexes")
packages_path = os.path.join(ROOT_FOLDER_NAME, "data")
logfile_path = os.path.join(working_path, "logs")
LastSeqFile = os.path.join(working_path,"__lastsequece")
logFileName = os.path.join(logfile_path,datetime.now().strftime('FailedList_%d-%m-%Y_%H_%M.log'))
DONWLOAD_CHUNK_SIZE_MB = 4   

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
def humanbytes(B):
   'Return the given bytes as a human friendly KB, MB, GB, or TB string'
   B = float(B)
   KB = float(1024)
   MB = float(KB ** 2) # 1,048,576
   GB = float(KB ** 3) # 1,073,741,824
   TB = float(KB ** 4) # 1,099,511,627,776
   if B < KB:
      return '{0} {1}'.format(B,'Bytes' if 0 == B > 1 else 'Byte')
   elif KB <= B < MB:
      return '{0:.2f} KB'.format(B/KB)
   elif MB <= B < GB:
      return '{0:.2f} MB'.format(B/MB)
   elif GB <= B < TB:
      return '{0:.2f} GB'.format(B/GB)
   elif TB <= B:
      return '{0:.2f} TB'.format(B/TB)

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

def UpdateLastSeqFile(sequncenumer):
    with open(LastSeqFile,'w') as f:
        f.write(str(sequncenumer))

def start(argv):
    # I want to get the path of app.py
    #base_path = os.path.dirname(os.path.realpath(__file__))

    if not os.path.exists(working_path):
        os.makedirs(working_path, exist_ok=True)
    if not os.path.exists(packages_path):
        os.makedirs(packages_path, exist_ok=True)
    if not os.path.exists(logfile_path):
        os.makedirs(logfile_path, exist_ok=True)
    
    print ("Connecting to SkimDB to get latest Stats...")
    r = requests.get(SkimDB_Main_Registry_Link, timeout=600)
    statsJson = json.loads(r.content)
    # print(statsJson)
    print ("Total Number of packages: "+ colored(str(statsJson['doc_count']),'red'))
    LatestSeq = "0"
    if os.path.exists(LastSeqFile):
        with open(LastSeqFile,'r') as ls:
            LatestSeq=  ls.readline()
    if LatestSeq == str(statsJson['committed_update_seq']):
        print (colored('No Updates since latest run, nothing to do...Bye','red'))
    ChangesFeedURLSuffix="_changes?feed=normal&style=all_docs&since=" + LatestSeq
    local_temp_file_name = os.path.join(working_path, "_changes.json")
    # make a backup of older file
    if os.path.exists(local_temp_file_name):
        shutil.copyfile(local_temp_file_name,local_temp_file_name+"_md5_"+GetMD5(local_temp_file_name)+".json")
    else:
        print (colored("I'm not downloading SkimDB _changes.json file, their connection is shit and unreliable, download it yourself from the link I provided, and paste the file into: %s" %(local_temp_file_name) ,'red'))
        exit (1)
    link = SkimDB_Main_Registry_Link + ChangesFeedURLSuffix
    print ("To Get Latest SkimDB updates, use this Download Link: %s" %(colored(link,'green')))
    # r = requests.get(link, stream=True)
    # block_size = 512 * 1024
    # wrote = 0 
    
    
    # with open(local_temp_file_name, 'wb') as f:
    #     for data in r.iter_content(block_size):
    #         if data:
    #             wrote += len(data)
    #             f.write(data)
    #             sys.stdout.write("Total Downloaded: "+ colored("%s"%humanbytes(wrote),'cyan') +"     \r")
    #             # sys.stdout.flush()
    # if wrote>0:
    #     sys.stdout.write("Total Downloaded: "+ colored("%s"%humanbytes(wrote),'cyan') +"     \r")
    #     print("")
    # test only
    # UpdateLastSeqFile(str(statsJson['committed_update_seq'])) # delete me later, we should do this at very late stage


    
    process_update(local_temp_file_name,LatestSeq)
    # # delete index.temp.json

    # os.remove(local_temp_file_name)
    return
    # installRequired.CheckRequiredModuels(required_modules)

# https://www.nuget.org/api/v2/package/vlc/1.1.8


# lock = Lock()


def WriteTextFile(filename,data):
    with open (filename,'w') as f:
        f.writelines(data)

def SaveAdnAppendToErrorLog(data):
    # timeS = datetime.now().strftime('FailedList__%H_%M_%d_%m_%Y.log.json')
    try:
        with open(logFileName, "a+") as outfile:
            outfile.write(data)
    except Exception as ex:
        print (ex)

ProcessPools = []

def signal_handler(sig, frame):
    print('\nYou pressed Ctrl+C!')
    print('\nTerminating All Processes')
    for p in ProcessPools:
        p.termincate()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def DownloadTar(package):
    AllGood = True
    Error = None
    numberOfTries = 0
    while numberOfTries<MaxNumberOfDownloadRetries:
        try:
            tarBallDownloadLink = package['link']
            # r = requests.get(tarBallDownloadLink, timeout=10)
            fname = tarBallDownloadLink.rsplit('/', 1)[-1]
            tarBallLocalFile=os.path.join(package['downloadPath'],fname)
            with requests.get(tarBallDownloadLink, stream=True,timeout=10) as r:
                r.raise_for_status()
                with open(tarBallLocalFile, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=DONWLOAD_CHUNK_SIZE_MB * 1024): 
                        if chunk: # filter out keep-alive new chunks
                            f.write(chunk)
            # with open(tarBallLocalFile, 'wb') as f:
            #     f.write(r.content)
            AllGood = True
            break
        except Exception as ex:
            AllGood = False
            #ErrorLog = "Sequence %d\n%s\n%s\n%s\n%s" % (item['seq'],package_name,item_rev, tarBallDownloadLink, ex)
            Error = ex
            # SaveAdnAppendToErrorLog(ErrorLog)
        numberOfTries += 1
    return AllGood,Error

def DownloadAndProcessesItemJob(item):
    package_name= item['id']
    packageFolderRoot = os.path.join(packages_path,item['id'])
    packageFolderTar = os.path.join(packageFolderRoot,"-")
    rev_file = os.path.join(packageFolderRoot,"__rev")
    item_rev=item['changes'][0]['rev'].strip()
    package_name_url_safe = urllib.parse.quote(package_name, safe='')
    json_index_file = os.path.join(packageFolderRoot,"index.json")
    # first we need to download the json file and name it as index.json
    if 'deleted' in item:
        if item['deleted']==True:
            if os.path.exists(packageFolderRoot):
                shutil.rmtree(packageFolderRoot)
            return # skip this item
    try:
        os.makedirs(packageFolderTar,exist_ok=True) # this will make all folders required, including "-" which is used to store the tar balls
    except Exception as ex:
        ErrorLog = "Sequence %d\n%s\n%s\n%s\n%s" % (item['seq'],package_name,item_rev, packageFolderTar, ex)
        SaveAdnAppendToErrorLog(ErrorLog)
        return
    
    # we will store a file indicating latest revision we processed
    CurrentRev=None
    # ShouldProcess=False
    if os.path.exists(rev_file):
        with open (rev_file,'r') as f:
            CurrentRev=f.readline().strip()
    if CurrentRev:
        if CurrentRev==item_rev:
            # print(colored("package '%s' with same rev %s number, will be skipped"%(item['id'],item_rev),'red'))
            return
    try:
        #write json index file
        downloadURL = SkimDB_Main_Registry_Link + package_name_url_safe
        r = requests.get(downloadURL,timeout=20)
        json_raw=r.content
        with open(json_index_file, 'wb') as f:
            f.write(json_raw)
        jsonObj = json.loads(json_raw)
        # now we will download all tar balls
        tars_to_download = []
        versions_dict = jsonObj['versions']
        for k in versions_dict:
            tarBallDownloadLink = versions_dict[k]['dist']['tarball']
            package = {"link": tarBallDownloadLink,"downloadPath":packageFolderTar}
            tars_to_download.append(package)
        DownloadPool = Pool(processes=MaxDownloadProcess)
        results = DownloadPool.imap(DownloadTar,tars_to_download)
        DownloadPool.close()
        DownloadPool.join()
        for r in results:
            allgood,errorvalue=r
            if allgood:
                WriteTextFile(rev_file,item_rev)
            else:
                ErrorLog = "Sequence %d\n%s\n%s\n%s\n%s" % (item['seq'],package_name,item_rev, tarBallDownloadLink, errorvalue)
                SaveAdnAppendToErrorLog(ErrorLog)

    except Exception as ex:
        ErrorLog = "Sequence %d\n%s\n%s\n%s\n%s" % (item['seq'],package_name,item_rev, downloadURL, ex)
        SaveAdnAppendToErrorLog(ErrorLog)
    
def GetStartingIndexForSorted(json_array,requriedValue):
    listofseqs = []
    for i in json_array:
        listofseqs.append(i['seq'])
    listofseqs.sort()
    array = np.asarray(listofseqs)
    value = int(requriedValue,10)
    idx = (np.abs(array - value)).argmin() # the reason I'm doing all of this, because there is a slight chance that the lastseq we are looking for no longer available, since it has been remove and replace by future seq. so we will take the one lower
    print ("Closest index found is: %s with value of: %s" %(colored(idx,'red'),colored(listofseqs[idx],'red'))  )
    return idx
    
def process_update(json_file,lastseq):
    global ProcessPools
    with open(json_file, 'r') as jsonfile:
        jsonObj = json.loads(jsonfile.read()) # this may take really long time, for the first run
        print(colored('Sorting out records, this may take some time...','red'))
        results = jsonObj['results']
        results_sorted = sorted(results, key=lambda k: k['seq'])
        print(colored('finished sorting','cyan'))
        print (colored('Processing items in batches','green'))
        print ("Last Proccessed Squence: %s  out of %s  \n"%(colored(lastseq,'cyan'),colored(jsonObj['last_seq'],'red'))  )
        results_sorted_from_lastseq = results_sorted[GetStartingIndexForSorted(results_sorted,lastseq):]
        results_sorted = None # clear it
        jsonObj = None # clear it
        starting_index = 0
        Batch_Index = 0
        All_records=len(results_sorted_from_lastseq)
        Total_Number_of_Batches = math.ceil(All_records/BatchSize)
        print (colored('Total Number of batches: %d with %d packages for each batch'%(Total_Number_of_Batches,BatchSize),'cyan'))
        while starting_index < All_records:
            Total_To_Process = BatchSize
            if All_records - starting_index < BatchSize:
                Total_To_Process = All_records - starting_index
                print (colored('Total to process less than Max Allowed, Changing total to: %d'% (Total_To_Process),'red'))
            print (colored("Processing Batch %d     of     %d"%(Batch_Index + 1,Total_Number_of_Batches)   ,'green'))
            itemBatch = results_sorted_from_lastseq[starting_index:starting_index+Total_To_Process]
            printIndex = 0
            packagesProcessString= "["
            for i in itemBatch:
                packagesProcessString += str(printIndex) + "-" + i['id'] + ","
                printIndex += 1
            packagesProcessString = packagesProcessString[:-2]
            packagesProcessString += "]"
            print (colored(packagesProcessString,'blue'))
            # ProcessPools = Pool(processes=MaxItemsToProcess)
             # we are processing package by package, each package will get multiple processes for downloading
            list(tqdm.tqdm(map(DownloadAndProcessesItemJob,
                                    itemBatch), total=len(itemBatch), ))

            # ProcessPools.close()
            # ProcessPools.join()
            starting_index += Total_To_Process
            Batch_Index += 1
            UpdateLastSeqFile(itemBatch[-1]['seq']) # last item sequence number in batch
         
        print(colored('Done :)','cyan'))

