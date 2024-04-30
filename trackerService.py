#!/usr/bin/python3
# trackerService.pu
# - 
APPNAME='TaskTracker'
APPDESC='Work task and activity tracker for manager work reporting and summarization'
VERSION='0.1.0'

##################################################################################
# IMPORTS
# Flask web service imports
from flask import Flask, render_template, request, redirect, send_from_directory
# Basic Functionality
import os, json, datetime, time, sys
# Data management and assistance
import inspect, csv, inspect

# import configparser
# - Think I want to just use json for config data and will write setup assist
#   services instead TODO?

##################################################################################
# DEFINITIONS
# General app definitions for global variable and filenames. 
# Don't use this section for configurables, this is only to ease internal dev
trackerConfigFile = 'trackerConfig.json'
trackerDataFile   = 'trackerData.json'
trackerConfig = {}
trackerConfigValues = [
  'ipAddr', 'port', 
  'workerName', 'workerEmail', 
  'managerName','managerEmail',
  'minActivitiesToSend','daysOfWeekToSend',
  'lastSentId', 'lastSentTime','lastSentFirstId'
]
cmdlineOptions = {
  'setup': 'Loads the first-run/setup wizard to configure application details',
  'help': 'Application help (this screen)',
  'send': 'Sends configured manager the work summary email for pending tasks',
  'test': 'Sends the worker a test email version of the manager email.'
}
webServiceData = {
  'APPNAME': APPNAME,
  'APPDESC': APPDESC,
  'VERSION': VERSION,
}

##############################################################################################
# FUNCTIONS Service Management
def dmesg(msg):
  # Allows for DEBUG environment variable to show 
  global DEBUG
  try:
    _ = DEBUG
  except Exception:
    DEBUG = False

  if os.getenv('DEBUG') or DEBUG:
    thisDateTime = datetime.datetime.now().strftime("%m%d%H%M")
    print(f'D:[ {thisDateTime} ] {inspect.stack()[1][3]}: {msg}')

def die(msg,noTraceBack=False,exitcode=99,subCall=False):
  # Calling die() with noTraceBack enabled will result in a quiet exit
  # Suppress traceback only for expect exit scenarios where we do not expect to need
  # any debug information.  
  global DEBUG
  try:
    _ = DEBUG
  except Exception:
    DEBUG = False

  # Parent module index / subCall allows us to wrapper die and still get real parent module
  callerIndex = 1
  if subCall:
    callerIndex += 1

  thisDateTime = datetime.datetime.now().strftime("%m%d%H%M")
  print(f'FATAL:{inspect.stack()[callerIndex][3]}() - {msg}')
  
  if noTraceBack and not DEBUG:
    # We don't want to suppress traceback if we're in debug mode
    exit(exitcode)
  else:
    print(f'\n##########################################################')
    raise Exception(f'FATAL CONDITION: {msg}')
  ## Just in case, finish with a hard exit, even though this line should never get processed
  exit(1)

def stopexec(msg,exitcode=99):
  # Wrapper function for clean die with no traceback
  die(msg,noTraceBack=True,exitcode=exitcode,subCall=True)
  ## Just in case, finish with a hard exit, even though this line should never get processed
  exit(1)

def get_timestamp_by_minute():
  s = "%Y%m%d%H%M"
  ts = time.mktime(datetime.datetime.strptime(time.strftime(s),s).timetuple())
  ts = int(ts)
  return ts

def get_datestr(ts,dateFmtStr='%Y-%m-%d %H:%M'):
  return datetime.datetime.fromtimestamp(ts).strftime(dateFmtStr)

def vardump(thisObj):
  print(json.dumps(thisObj,indent=2))

##############################################################################################
# FUNCTIONS Configuration Management
def loadConfig():
  global trackerConfig
  global trackerConfigFile
  # Check config file exists
  if not os.path.isfile(trackerConfigFile):
    dmesg(f'Config file not found: {trackerConfigFile} - Attmeping fresh setup...')
    if not start_setup():
      # Better error handling when? TODO
      die(f'The start_setup workflow returned in a False status instead of asserting.  This shouldnt happen.')

  # Load the config in from the config file
  dmesg(f'Loading tracker configuration from {trackerConfigFile}')
  try:
    with open(trackerConfigFile,'r') as cfgFile:
      trackerConfig = json.load(cfgFile)
  except Exception as e:
    die(f'Config load failed for some reason: {Exception(e)}')
  
  validateConfig()

  dmesg(f'Loaded {len(trackerConfig)} elements for configuration.')
  
  return True
  
def validateConfig():
  global trackerConfig
  # Validate that trackerConfig has all expected values
  badConfig = False
  for trackerConfigValue in trackerConfigValues:
    if not trackerConfigValue in trackerConfig.keys():
      badConfig = True
      print(f'ERROR: Missing \'{trackerConfigValue}\' in configuration data.')
  if badConfig:
    print(f'Please re-run setup or correct the configuration in \n\t{os.path.abspath(trackerConfigFile)}')
    stopexec('Unable to proceed due to missing configuration values.')
  
  # TODO Add additional validation for email addresses and stuff later
  return True

def saveConfig():
  global trackerConfig
  global trackerConfigFile
  
  # Before we just save, need to do a little validation and default value population
  if not 'daysOfWeekToSend' in trackerConfig.keys():
    trackerConfig['daysOfWeekToSend'] = ['Mon','Tue','Wed','Thu','Fri']
  if not 'lastSentId' in trackerConfig.keys():
    trackerConfig['lastSentId'] = 0
  if not 'lastSentTime' in trackerConfig.keys():
    trackerConfig['lastSentTime'] = 0
  if not 'lastSentFirstId' in trackerConfig.keys():
    trackerConfig['lastSentFirstId'] = 0

  if not validateConfig():
    die('Unable to validate configuration values - Also validateConfig() did not exit as expected.')
  
  try:
    with open(trackerConfigFile,'w') as cfgFile:
      cfgFile.write(json.dumps(trackerConfig,indent=2))
  except Exception as e:
    die(f'Failed to write config file - {Exception(e)}')



##############################################################################################
# FUNCTIONS Command Line Flow Operations
def start_setup(firstCall=True):
  global trackerConfig
  # Initial run/cmdline setup workflow
  # Print introduction if this is the first call
  if firstCall:
    print(f'{"="*80}')
    print(f'Setup Assistant for {APPNAME}')
    print('-')
    print('This assistant will step you through setting up the configuration values')
    print('for this application.  You can re-run this wizard manually by running')
    print(f'\t{sys.argv[0]} setup\n')
  
  print(f'Service IP Address')
  print(f'Specify the IP address the webUI should listen on.  The default 0.0.0.0')
  print(f'will cause the web service to bind on all available IPs on this server.')
  ipAddr = input('IP Address (0.0.0.0) > ')
  if not ipAddr:
    ipAddr = '0.0.0.0'
  else:
    # TODO we need to do some kind of input validation here
    pass
  
  print(f'\nService Port')
  print(f'Specify the Port the webUI should attach to.  This value must be above 2000')
  print(f'and not in use by any other service on the server.')
  port = input('TCP Port (3131) > ')
  if not port:
    port = 3131
  # Validate the port ID is valid
  try:
    port = int(port)
    if not port > 2000 or not port < 65535:
      stopexec(f'Invalid port ID value: Must be an integer between 2001 and 65535')
  except ValueError:
    stopexec(f'Invalid port ID value: Must be an integer between 2001 and 65535')

  print(f'\nWorker Name and Email: This is the agent whose work is being tracked (you)')
  workerName = input('  Name > ')
  workerEmail = input('*Email > ')
  if not workerEmail:
    stopexec(f'Worker Email address is required.')
  print(f'\nManager Name and Email: This is the recipient of the work summaries')
  managerName = input('  Name > ')
  managerEmail = input('*Email > ')
  if not managerEmail:
    stopexec(f'Manager Email address is required.')
  print()
  print('Enter minimum number of activities required to generate a manager email.')
  print('The default value is 3.')
  minActivitiesToSend = input('> ')
  if not minActivitiesToSend:
    minActivitiesToSend = 3
  else:
    minActivitiesToSend = int(minActivitiesToSend)
  
  print('-')
  print('Settings Values:')
  print(f'ServerListen:\thttp://{ipAddr}:{port}')
  print(f'      Worker:\t{workerName} {workerEmail}')
  print(f'     Manager:\t{managerName} {managerEmail}')
  print(f'Minimum pending activities to send for reports: {minActivitiesToSend}')
  response = input('\nAre these settings correct? (y/N) ')
  if not response:
    if not start_setup(False):
      die(f'Setup failed for some reason.')
  if not response[0].upper() == 'Y':
    if not start_setup(False):
      die(f'Setup failed for some reason.')
  
  # Populate values in the in-memory configuration
  trackerConfig['ipAddr'] = ipAddr
  trackerConfig['port'] = port
  trackerConfig['workerName'] = workerName
  trackerConfig['workerEmail'] = workerEmail
  trackerConfig['managerName'] = managerName
  trackerConfig['managerEmail'] = managerEmail
  trackerConfig['minActivitiesToSend'] = minActivitiesToSend
  
  # Trigger the config save and return a good status
  saveConfig()
  return True
  
def show_cmdline_usage(errMsg=None):
  if errMsg:
    print(f'{errMsg} - Use the \'help\' module to show help')
  print(f'Usage: {sys.argv[0]} [module]')
  if not errMsg:
    print(f'{APPNAME} tracking and reporting system for management work summaries')
    print()
    print(f'When no module is specified, the tracker\'s web service will be started.')
    print(f'Modules can be specified for certain commandline operations and tasks.')
    print()
    for cmdlineOption in cmdlineOptions:
      print(f'{cmdlineOption.rjust(10)}{" "*4}{cmdlineOptions[cmdlineOption]}')
    print()
  exit()

##############################################################################################
# FUNCTIONS Tracker Data Activity Management
# trackerDataFile

def getTrackerData():
  global trackerConfig
  loadConfig()
  if not os.path.isfile(trackerDataFile):
    dmesg('Missing tracker data file - Creating a new, empty data file')
    with open(trackerDataFile,'w') as dataFile:
      dataFile.write('{}\n')
  # Load the trackerData directly as json
  try:
    with open(trackerDataFile,'r') as dataFile:
      trackerData = json.load(dataFile)
  except Exception as e:
    die(f'Encountered error while trying to load tracker data file: {os.path.abspath(trackerDataFile)} - File may be corrupted and require correction or removal.')
  dmesg(f'Loaded {len(trackerData)} data items from {trackerDataFile}')
  if len(trackerData) < 1:
    trackerData = False
  return trackerData

def emptyTrackerItem():
  trackerItem = {
    'itemId': '',
    'itemTag': '',
    'itemTicket': '',
    'itemTime': '',
    'itemDesc': '',
  }
  return trackerItem

def saveNewTrackerItem(data):
  # create empty tracker item data structure
  trackerItem = {
    'itemId': None,
    'itemTime': None,
    'itemTag': None,
    'itemTicket': None,
    'itemDesc': None,
    'itemSent': False,
    'itemSentTime': None
  }
  # Find next available item ID
  trackerItem['itemId'] = getNextTrackerItemId()
  trackerItem['itemTime'] = get_timestamp_by_minute()
  trackerItem['itemTag'] = data['itemTag']
  trackerItem['itemTicket'] = data['itemTicket']
  trackerItem['itemDesc'] = data['itemDesc']
  trackerItems = getTrackerData()
  if not trackerItems:
    trackerItems = []
  trackerItems.append(trackerItem)
  with open(trackerDataFile,'w') as dataFile:
    dataFile.write(json.dumps(trackerItems,indent=2))
  return True



def getNextTrackerItemId():
  trackerItems = getTrackerData()
  highestItemId = 0
  if trackerItems:
    for trackerItem in trackerItems:
      if trackerItem['itemId'] > highestItemId:
        highestItemId = trackerItem['itemId']
  return highestItemId + 1


##############################################################################################
# FLASK WEB SERVICE DEFINITIONS AND ROUTES
webService = Flask(__name__)

# favicon redirect
@webService.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(webService.root_path, 'static'),'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Main Page route definition
@webService.route('/')
def wwwOut_main():
  global webServiceData
  trackerData = getTrackerData()
  resultMsg = stageResultMsg()
  return render_template('main.html', webServiceData=webServiceData, pagename="Main",
      trackerData=trackerData, trackerItem=emptyTrackerItem(),resultMsg=resultMsg)

@webService.route('/newitem',methods=['POST'])
def wwwIn_newitem():
  global webServiceData
  data = request.form
  # validate data
  if not data['itemTag'] or not data['itemDesc']:
    webServiceData['resultMsg'] = 'Category and Description are required fields, only ticket is optional.'
  else:
    newItemId = saveNewTrackerItem(data)
    if not newItemId:
      webServiceData['resultMsg'] = 'Error encountered while trying to save new item, see service logs for details.'
    else:
      webServiceData['resultMsg'] = f'New activity item {newItemId} added and set to pending transmission.'
  return redirect('/',code=302)

def stageResultMsg():
  global webServiceData
  resultMsg = False
  if 'resultMsg' in webServiceData.keys():
    if webServiceData['resultMsg']:
      resultMsg = webServiceData['resultMsg']
  webServiceData['resultMsg'] = False
  return resultMsg

##############################################################################################
# RUNTIME 
# Check command line options before entering the __main__ segment
if len(sys.argv) > 1:
  cmdlineOption = sys.argv[1].lower()
  if not cmdlineOption in cmdlineOptions.keys():
    show_cmdline_usage(f'Invalid commandline option: {sys.argv[1]}')
  
  if cmdlineOption == 'setup':
    start_setup()
    exit()
  if cmdlineOption == 'test':
    print(f'TODO: TEST email')
    exit()
  if cmdlineOption == 'send':
    print(f'TODO: Send manager email.')
    exit()

  # If we got here, a cmdlineOption is configured in cmdlineOptions but isn't being
  #  caught for function here. 
  die(f'Sorry, \'{cmdlineOption}\' appears to be a valid option but no module is available to execute.')


if __name__ == '__main__':
  # CONFIG CHECK
  # Before launching the web service, we need to check if this is a first-run, or if the
  #   configuration has become corrupted.  Attempt to load the config
  loadConfig()

  trackerData = getTrackerData()
  
  # Start the web service
  webService.run(host=trackerConfig['ipAddr'],port=trackerConfig['port'],debug=True)





