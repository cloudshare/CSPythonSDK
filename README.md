CloudShare Python SDK API and API CLI
=====================================

## Description

1. An SDK for developing applications in Python to connect to the CloudShare service using the CloudShare REST API. 2. A CLI (Command Line Interface) executable to communicate with the CloudShare service via Windows machines.

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

'Python\cloudshare' folder contains a command line tool that uses `CSHighApi`, `CSLowApi` and `Cement` framework. It used to run API calls and returns raw JSON responses or human readable responses to standard output.
    
	usage: python cloudshare <CMD> -opt1 --opt2=VAL [arg1] [arg2] ...

    CloudShare API client

    commands:

      cf
        Cloud Folders

      config
        Configuration settings edit

      create
        Create Environment

      createsnapshot
        Create Snapshots

      env
        Environment

      login
        Login

      rdp
        RDP

      snapshot
        Snapshots

      tmpl
        Templates

      vm
        Virtual Machines

    optional arguments:
      -h, --help            show this help message and exit
      --debug               toggle debug output
      --quiet               suppress all output
      -f FORMATTING, --formatting FORMATTING
                            Output formatting options, default is RAWJSON

## Requirements

* Python 2.7 or 3.2 (we recommend adding Python folder to system's path)
* API-ID (assigned by CloudShare)
* API-KEY (assigned by CloudShare)

## Installation

We support two usage options:

1. Running the CLI from source code:

 Install `Cement` framework:
    
    1. If you have pip installed simply run 'pip install cement', if you don't, move to step 2+3:
    
    2. Download and run https://bitbucket.org/pypa/setuptools/downloads/ez_setup.py

    3. Run c:\<PythonFolder>\Scripts>easy_install.exe cement
    
    use 'python cloudshare' to start from the SDK folder in order to start using the CloudShare CLI
    
    you can read more about `Cement` framework here: http://builtoncement.com/2.0/

2. Running the CLI executable:

 Go to WindowsCLI folder
 
 Verify 'config.conf' file is located in the same folder of 'cloudshare.exe' executable file
 
 Go to the SDK folder
 
 Use 'cloudshare.exe' to run the commands

## Configuration file
    
After installation please locate `config.conf` file, and make sure it contains your valid credentials and the correct api host and version.(Default values are set to: host = use.cloudshare.com, version = v2)

You can choose which formatting type will be the client's default - the raw JSON (*RAWJSON*) or a more human readable format (*FORMATTED*)

## Usage example

1. Create a new environment from existing snapshot
        
        $ python cloudshare create options -p=projectA -f=FORMATTED
        OJ0N5LE3J2BB - [projectA] On Demand 2h/6h
            ProtoTest:
                5O5FJXSQMJRA - Jhon's Snapshot (7/10/2012 11:31 AM)
                VYTWIFLW2MJB - Mike's fifth Snapshot (9/23/2012 8:16 AM)

        ACCWHDVMU14B - [projectA] On Demand - 3h/9h
            ServerTests:
                VBRWBWR3BDOA - Jhon's Snapshot (7/15/2012 3:26 AM)

        $ python python cloudshare create env -c=OJ0N5LE3J2BB -s=5O5FJXSQMJRA -n="my shiny new environment" -p=projectA --f=FORMATTED
        Environment is being created from snapshot
        
2. Create a new empty environment and add machines to it
        
        $ python cloudshare info projectslist
        projectA
        projectB
        projectC
        
        $ python cloudshare create empty -n=myNewEnv -pn=projectB -d="short description"
        Empty environment is being created
        
        $ python cloudshare tmpl list -f=FORMATTED
        JV5CJGF2SCVA - Windows server / Windows / [CPUs:1 Disk:12GB RAM:512MB]
        V01QEX4LMZ2A - Windows server 2008 / Windows / [CPUs:1 Disk:12GB RAM:512MB]
        EBHHCUZVJS0A - Automation / Windows / [CPUs:1 Disk:12GB RAM:512MB]
        ZAHYPZNEC3RA - CentOS 5 With KDE2 / Linux / [CPUs:1 Disk:20GB RAM:1024MB]
        
        $ python cloudshare info list -f=FORMATTED
        UOPRE1LX1E2B - myNewEnv of projectB (Ready)
        XCHXQC2RWUBB - Testing of projectB (Not ready)
        
        $ python cloudshare tmpl add -i=UOPRE1LX1E2B -t=JV5CJGF2SCVA -n="my new machine" -f=FORMATTED
        Machine is being added from template
            
        $ python cloudshare tmpl add -i=UOPRE1LX1E2B -t=ZAHYPZNEC3RA -n="my second machine" -f=FORMATTED
        Machine is being added from template

## Under the hood

The example below shows how the CLI works - it makes High Level API to send the *ListEnvironments* REST API request to the server to obtain
a list of all the user's environments, then send a *GetEnvironmentState* request for each environment in the list. 
The responses are filtered to show a list of the state of each environment.

	from csapi.cshighapi import CSHighApi

    api = CSHighApi(api_key, api_id)
    
    envs = api.get_environment_status_list()
    for env in envs:
        print(env['name'])

## References

[CloudShare REST API](http://docs.cloudshare.com/rest-api/v2/overview/)

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

Cement license

    Copyright (c) 2009-2012, BJ Dierkes All rights reserved

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.