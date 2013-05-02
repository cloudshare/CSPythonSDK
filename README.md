CloudShare Python SDK API
=====================

## Description

An SDK for developing applications in Python to connect to the CloudShare service using the CloudShare REST API. The SDK
interfaces to the CloudShare API and tries to present a useful Python API for developers. 

The SDK includes Python methods for the following API activities:

* Creating and Managing Environments and VMs
* Taking Snapshots
* Using CloudFolders
 
The SDK has three modes of use: 

### High Level API

The High Level API (`CSHighApi` class) implements the most popular REST API calls. It also parses the JSON response blocks into Python dictionaries. 
See the example below.

### Low Level API 

The Low Level API (`CSLowApi` class) provides a way to easily create and send REST API requests. It handles the authentication required
by the CloudShare REST API. The `call()` method in `CSHighApi` can be used to call the CloudShare API.

### Command line

`cscl.py` is a command line tool that uses `CSLowApi`. It prints the raw JSON responses to standard output and shows you the URL it uses.

	usage: cscl.py [-h] -i API-ID -k API-KEY -m CATEGORY -c COMMAND
	               [-p [KEY VALUE [KEY VALUE ...]]] [-f]

	CloudShare API command line utility

	optional arguments:
	  -h, --help            show this help message and exit
	  -i API-ID, --id API-ID
	                        CloudShare API ID
	  -k API-KEY, --key API-KEY
	                        CloudShare API Key
	  -m CATEGORY, --category CATEGORY
	                        The API command category
	  -c COMMAND, --command COMMAND
	                        The API command
	  -p [KEY VALUE [KEY VALUE ...]], --params [KEY VALUE [KEY VALUE ...]]
	                        Command's parameters. List of key-value pairs
	  -f, --fire            Execute API call

	Example:
		$ python cscl.py -i MYAPIID -k MYAPIKEY -m env -c ListEnvironments -f


## Requirements

* Python 2.7 or 3.2
* API-ID (assigned by CloudShare)
* API-KEY (assigned by CloudShare)

## Usage example

The example below uses the High Level API to send the *ListEnvironments* REST API request to the server to obtain
a list of all the user's environments, then send a *GetEnvironmentState* request for each environment in the list. 
The responses are filtered to show a list of the state of each environment.

	from csapi.cshighapi import CSHighApi

    api = CSHighApi(api_key, api_id)
    
    envs = api.get_environment_status_list()
    for env in envs:
        print(env['name'])


## References

[CloudShare REST API](http://docs.cloudshare.com)

License 
=======

Copyright 2013 CloudShare, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

