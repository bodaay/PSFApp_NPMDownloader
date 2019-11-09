# PSFApp_NPMDownloader

# The script is packaged with PSF template, a template I created to store all your files in the (app) folder in a single python file.
# you can always add more files to app folder, run: SCRIPTNAME update, and it will repackages itself with all files in the folder.
# at the end, you can just distribute a single text file


if you work in banks or any other airgapped enviroments, you understand how much you would love to have the ability to just do
npm install package_name 



Since I couldn't find any proper tool to fully replicate NPM registry, I decided to write this simple script to do so
With the ability to stop the download anytime, then continue, SHA checksum of downloads, and ability to check all failed packages in easy way



The script will output as well nginx sample configuration you can use later on in your airgapped enviroment, 

The reason why I don't like to change origianl index.json files links, is because I want to have flexbility in changes the hostname without 
going through all downloaded json files again and again, nginx direct subsitiution of json files works flawlessly

The script will keep storing a file names __lastsequence, this is actually your main tracking of download progress

This file will be updated after completing a batch

with a configured paramters, this file will also be backed up ever X batches

