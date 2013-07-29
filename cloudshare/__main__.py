from cement.core import foundation, backend, controller, handler, interface, arg
from csapi.cslowapi import ApiException, prettify_json
from csapi.cshighapi import CSHighApi
import os
import sys
import json
import tempfile
import subprocess
import time

def main():

    api = None

    #======================================================================================================================================
    #== Utility functions
    #====================================================================================================================================== 

    # Used to output the Json responses
    def sendToOutput(content, args, printFormattedFunc = None):
        
        type = 'RAWJSON'
        
        if app.config.has_section('output') and app.config.has_key('output', 'type'):
            confType = app.config.get_section_dict('output')['type']
            if confType == 'RAWJSON' or confType == 'FORMATTED':
                type = confType

        if args.formatting:
            type = args.formatting

        if type == 'RAWJSON':
            print json.dumps(content, sort_keys=True, indent=4, separators=(',', ': '))
        else:
            if type == 'FORMATTED' and printFormattedFunc:
                printFormattedFunc(content)
            else:
                sys.stderr.write('Missing command name to format, printing as Json')
                print json.dumps(content, sort_keys=True, indent=4, separators=(',', ': '))
    
    # Extract arg and empty string if not exsited
    def getArg(arg):
        if arg:
            return arg
        else:
            return ''
            
    def module_path():
        #This will get us the program's directory, even if we are frozen using py2exe

        if hasattr(sys, "frozen"):
            return os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding( )))

        return os.path.dirname(unicode(__file__, sys.getfilesystemencoding( )))
    
    # Get configuration file name
    def getConfigFile():
        #print os.path.dirname(os.path.abspath(__file__)) + '\config.conf'
        #return os.getcwd() + '\cloudshare\\' + 'config.conf'
        return module_path() + '\config.conf'
    
    # Confirmation notification
    def areYouSure(action):
        descision = raw_input('Are you sure you want to ' + action + '? (y/n)')
        if descision=='y':
            return True
        else:
            print 'Action canceled'
            return False
     
    # Creates and execute a RDP file 
    def rdpConnect(data):
        import win32crypt
        import binascii
        import win32cryptprotect

        rdpFileData = data['rdp']
        password = data['clearTextPassword']
        
        pwdHash=win32cryptprotect.cryptData(password)
        rdpFileData = rdpFileData.replace("<PASSWORD>", pwdHash)
        fhandle, fname = tempfile.mkstemp(suffix='.rdp')
        f = os.fdopen(fhandle,'w')
        f.write(rdpFileData)
        f.close()
        
        subprocess.Popen(['mstsc',fname,])
        time.sleep(2)
        os.unlink(fname)

    # Cleanup dictionary from None values
    def cleanupDictionary(dic):
        for key in dic.keys():
            if not dic[key]:
                dic[key] = 'None'
        return dic
        
    #======================================================================================================================================
    #== Base Controller
    #======================================================================================================================================
    class MyAppBaseController(controller.CementBaseController):
        class Meta:
            label = 'base'
            description = "CloudShare API client"
            arguments = [ ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options, default is RAWJSON') ), ]

        @controller.expose(hide=True, aliases=['run'])
        def default(self):
            print 'Available commands: info | env | vm | create | snapshot | createsnapshot | tmpl | cf | login | rdp | config'

    #======================================================================================================================================
    #== Info Controller
    #====================================================================================================================================== 
    
    def printFormattedList(content):
        for env in content:
            env = cleanupDictionary(env)
            print env['envId'] + ' - ' + env['name'] + ' of ' + env['project'] + ' (' + env['status_text'] + ')'
                
    def printFormattedState(content):
        content = cleanupDictionary(content)
        print content['envId'] + ' - ' + content['name'] + ' (' + content['status_text'] + ')'
        print 'vms:'
        for vm in content['vms']:
            vm = cleanupDictionary(vm)
            status = vm['status_text']
            if status == 'In progress' and vm['progress']:
                status = str(vm['progress']) + '%'
            print '    ' + vm['vmId'] + ' - ' + vm['name'] + ' (' + status + ')'
     
    class InfoController(controller.CementBaseController):

        class Meta:
            label = 'info'
            interface = controller.IController
            stacked_on = None
            description = "Entities Information"
            arguments = [ ( ['-i', '--envId'], dict(dest='envId', help='environment id') ),
                          ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options, default is RAWJSON') ),]

        @controller.expose(help="command under the info base namespace", hide=True)
        def default(self):
            print 'Available commands: list | state | projectsList'
        
        @controller.expose(help="List your environments")
        def list(self):
            sendToOutput(api.list_environments(), self.pargs, printFormattedList)
            
        @controller.expose(help="Get environment state")
        def state(self):
            
            if self.pargs.envId:
                sendToOutput(api.get_environment_status(self.pargs.envId), self.pargs, printFormattedState)
            else:
                print 'Usage: info state -i=<ENV_ID>'

        @controller.expose(help="Get projects list")
        def projectsList(self):
            projectsData = api.create_ent_app_env_options('', '', '')
            prList = set()
            for projectPrototypeResourcePackage in projectsData:
                projectPrototypeResourcePackage = cleanupDictionary(projectPrototypeResourcePackage)
                prList.add(projectPrototypeResourcePackage['Project'])
            for pr in prList:
                print pr

    #======================================================================================================================================
    #== Environment Controller
    #======================================================================================================================================  
    
    def printFormattedEnvResume(content):
        if content and content['envId']:
            print 'Environment is being resumed'
            
    def printFormattedEnvSuspend(content):
        if content and content['envId']:
            print 'Environment is being suspended'
            
    def printFormattedEnvExtend(content):
        if content and content['envId']:
            print 'Environment is extending'
            
    def printFormattedEnvRevert(content):
        if content and content['envId']:
            print 'Environment is being reverted'
            
    def printFormattedEnvDelete(content):
        if content and content['envId']:
            print 'Environment is being deleted'
            
    class EnvController(controller.CementBaseController):

        class Meta:
            label = 'env'
            interface = controller.IController
            stacked_on = None
            description = "Environment Management"
            arguments = [ ( ['-i', '--envId'], dict(dest='envId', help='environment id') ), ( ['-s', '--snapshotId'], dict(dest='snapshotId', help='snapshot id') ),
                        ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options, default is RAWJSON') ),
                        ( ['-c'], dict(dest='noConfirm', help='no confirmations', action='store_true') ),]

        @controller.expose(help="command under the env base namespace", hide=True)
        def default(self):
            print 'Available commands: resume | suspend | extend | revert | revertto | delete'
        
        @controller.expose(help="Resume environment")
        def resume(self):
            if self.pargs.envId:
                sendToOutput(api.resume_environment(self.pargs.envId), self.pargs, printFormattedEnvResume)
            else:
                print 'Usage: env resume -i=<ENV_ID>'

        @controller.expose(help="Suspend environment")
        def suspend(self):
            if self.pargs.envId:
                sendToOutput(api.suspend_environment(self.pargs.envId), self.pargs, printFormattedEnvSuspend)
            else:
                print 'Usage: env suspend -i=<ENV_ID>'

        @controller.expose(help="Extend environment time")
        def extend(self):
            if self.pargs.envId:
                sendToOutput(api.extend_environment(self.pargs.envId), self.pargs, printFormattedEnvExtend)
            else:
                print 'Usage: env extend -i=<ENV_ID>'

        @controller.expose(help="Revert environment")
        def revert(self):
            if self.pargs.envId:
                if self.pargs.noConfirm or areYouSure('revert this environment'):
                    sendToOutput(api.revert_environment(self.pargs.envId), self.pargs, printFormattedEnvRevert)
            else:
                print 'Usage: env revert -i=<ENV_ID> [-c]'

        @controller.expose(help="Revert environment into a specific snapshot")
        def revertto(self):
            if self.pargs.envId and self.pargs.snapshotId:
                if self.pargs.noConfirm or areYouSure('revert this environment'):
                    sendToOutput(api.revert_environment_to_snapshot(self.pargs.envId, self.pargs.snapshotId), self.pargs, printFormattedEnvRevert)
            else:
                print 'Usage: env revertto -i=<ENV_ID> -s=<SNAPSHOT_ID> [-c]'

        @controller.expose(help="Delete environment")
        def delete(self):
            if self.pargs.envId:
                if self.pargs.noConfirm or areYouSure('delete this environment'):
                    sendToOutput(api.delete_environment(self.pargs.envId), self.pargs, printFormattedEnvDelete)
            else:
                print 'Usage: env delete -i=<ENV_ID> [-c]'

    #======================================================================================================================================
    #== Vm Controller
    #====================================================================================================================================== 
    
    def printFormattedVmDelete(content):
        if content and content['vmId']:
            print 'VM is being deleted'
            
    def printFormattedVmRevert(content):
        if content and content['vmId']:
            print 'VM is being reverted'
            
    def printFormattedVmReboot(content):
        if content and content['vmId']:
            print 'VM is being rebooted'

    def printFormattedVmExecPath(content):
        if content and content['executed_path']:
            print 'Script is being executed on VM'
            
    class VmController(controller.CementBaseController):

        class Meta:
            label = 'vm'
            interface = controller.IController
            stacked_on = None
            description = "Manage your VMs"
            arguments = [ ( ['-i', '--envId'], dict(dest='envId', help='environment id') ), ( ['-v', '--vmId'], dict(dest='vmId', help='virtual machine id') ), ( ['-s', '--scriptPath'], dict(dest='scriptPath', help='script path') ),
                        ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options, default is RAWJSON') ),
                        ( ['-c'], dict(dest='noConfirm', help='no confirmations', action='store_true') ),]

        @controller.expose(help="command under the vm base namespace", hide=True)
        def default(self):
            print 'Available commands: delete | revert | reboot | execute'
        
        @controller.expose(help="Delete vm")
        def delete(self):
            if self.pargs.envId and self.pargs.vmId:
                if self.pargs.noConfirm or areYouSure('delete this vm'):
                    sendToOutput(api.delete_vm(self.pargs.envId, self.pargs.vmId), self.pargs, printFormattedVmDelete)
            else:
                print 'Usage: vm delete -i=<ENV_ID> -v=<VM_ID> [-c]'

        @controller.expose(help="Revert vm")
        def revert(self):
            if self.pargs.envId and self.pargs.vmId:
                sendToOutput(api.revert_vm(self.pargs.envId, self.pargs.vmId), self.pargs, printFormattedVmRevert)
            else:
                print 'Usage: vm revert -i=<ENV_ID> -v=<VM_ID>'
                
        @controller.expose(help="Reboot vm")
        def reboot(self):
            if self.pargs.envId and self.pargs.vmId:
                sendToOutput(api.reboot_vm(self.pargs.envId, self.pargs.vmId), self.pargs, printFormattedVmReboot)
            else:
                print 'Usage: vm reboot -i=<ENV_ID> -v=<VM_ID>'
                
        @controller.expose(help="Execute script on vm")
        def execute(self):
            if self.pargs.envId and self.pargs.vmId and self.pargs.scriptPath:
                sendToOutput(api.execute_path(self.pargs.envId, self.pargs.vmId, self.pargs.scriptPath), self.pargs, printFormattedVmExecPath)
            else:
                print 'Usage: vm execute -i=<ENV_ID> -v=<VM_ID> -s=<SCRIPT_PATH>'

    #======================================================================================================================================
    #== CloudFolders Controller
    #======================================================================================================================================              
    def printFormattedCloudFoldersInfo(content):
        content = cleanupDictionary(content)
        print content['uri']
        print 'Private folder name: ' + content['private_folder_name']
        print 'quota :' + content['quota_in_use_gb'] + '/' + content['total_quota_gb'] + ' GB'
        
    def printFormattedCfMount(content):
        if content and content['apiId']:
            print 'CloudFolder is being mounted'
            
    def printFormattedCfUnmount(content):
        if content and content['apiId']:
            print 'CloudFolder is being unmounted'
            
    def printFormattedCloudFoldersMountExt(content):
        content = cleanupDictionary(content)
        print content['uri']
        print 'quota :' + content['quota_in_use_gb'] + '/' + content['total_quota_gb'] + ' GB'
        print 'Private folder name: ' + content['private_folder_name']
        if content['isActionComplete']:
            print 'Windows folder: ' + content['windowsFolder']
            print 'Linux folder: ' + content['linuxFolder']
            
    class CloudfoldersController(controller.CementBaseController):

        class Meta:
            label = 'cf'
            interface = controller.IController
            stacked_on = None
            description = "Cloud folders actions"
            arguments = [ ( ['-i', '--envId'], dict(dest='envId', help='environment id') ), ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options, default is RAWJSON') ),]

        @controller.expose(help="command under the cf base namespace", hide=True)
        def default(self):
            print 'Available commands: info | mount | unmount | mountext'
        
        @controller.expose(help="CloudFolders info")
        def info(self):
            sendToOutput(api.get_cloudfolders_info(), self.pargs, printFormattedCloudFoldersInfo)

        @controller.expose(help="Mount environment")
        def mount(self):
            if self.pargs.envId:
                sendToOutput(api.mount(self.pargs.envId), self.pargs, printFormattedCfMount)
            else:
                print 'Usage: cf mount -i=<ENV_ID>'
                
        @controller.expose(help="Unmount environment")
        def unmount(self):
            if self.pargs.envId:
                sendToOutput(api.unmount(self.pargs.envId), self.pargs, printFormattedCfUnmount)
            else:
                print 'Usage: cf unmount -i=<ENV_ID>'
                
        @controller.expose(help="Mount environment, and fetch additional info")
        def mountext(self):
            if self.pargs.envId:
                sendToOutput(api.mount_and_fetch_info_ext(self.pargs.envId), self.pargs, printFormattedCloudFoldersMountExt)
            else:
                print 'Usage: cf mountext -i=<ENV_ID>'
                
    #======================================================================================================================================
    #== Template Controller
    #======================================================================================================================================         
    
    def printFormattedTmplList(content):
        for template in content['templatesList']:
            template = cleanupDictionary(template)
            print template['id'] + ' - ' + template['name'] + ' / ' + template['os_type_string'] + ' / [CPUs:' + str(template['num_cpus']) + ' Disk:' + str(template['disk_size_gb']) + 'GB RAM:' + str(template['memory_size_mb']) + 'MB]'
    
    def printFormattedTmplAddToEnv(content):
        if content and content['envId']:
            print 'Machine is being added from template'
    
    class TemplateController(controller.CementBaseController):

        class Meta:
            label = 'tmpl'
            interface = controller.IController
            stacked_on = None
            description = "Templates actions"
            arguments = [ ( ['-i', '--envId'], dict(dest='envId', help='environment id') ),
                        ( ['-t', '--tmplId'], dict(dest='tmplId', help='template id') ),
                        ( ['-n', '--newVmName'], dict(dest='newVmName', help='new vm name') ),
                        ( ['-d', '--description'], dict(dest='description', help='new vm description') ),
                        ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options, default is RAWJSON') )]

        @controller.expose(help="command under the tmpl base namespace", hide=True)
        def default(self):
            print 'Available commands: list | add'

        @controller.expose(help="List available templates")
        def list(self):
            sendToOutput(api.list_templates(), self.pargs, printFormattedTmplList)

        @controller.expose(help="Add a vm to an existing environment based on a given template")
        def add(self):
            description = getArg(self.pargs.description)
            if self.pargs.envId and self.pargs.tmplId and self.pargs.newVmName:
                sendToOutput(api.add_vm_from_template(self.pargs.envId, self.pargs.tmplId, self.pargs.newVmName, description), self.pargs, printFormattedTmplAddToEnv)
            else:
                print 'Usage: tmpl add -i=<ENV_ID> -t=<TEMPLATE_ID> -n=<NEW_VM_NAME> [-d=<NEW_VM_DESCRIPTION>]'
                
           
    #======================================================================================================================================
    #== Create Controller
    #======================================================================================================================================   
    
    def printFormattedCreateOptions(content):
        
        for projectPrototypeResourcePackage in content:
            projectPrototypeResourcePackage = cleanupDictionary(projectPrototypeResourcePackage)
            print projectPrototypeResourcePackage['EnvironmentPolicyId'] + ' - [' + projectPrototypeResourcePackage['Project'] + '] ' + projectPrototypeResourcePackage['EnvironmentPolicyDuration']
            for blueprint in projectPrototypeResourcePackage['Blueprints']:
                blueprint = cleanupDictionary(blueprint)
                print '    ' + blueprint['Name'] + ':'
                for snapshot in blueprint['Snapshots']:
                    snapshot = cleanupDictionary(snapshot)
                    print '        ' + snapshot['SnapshotId'] + ' - ' + snapshot['Name'] + ' (' + snapshot['CreationTime'] + ')'
            print '\n'

    def printFormattedCreateEnv(content):
        if content and content['environmentPolicyId']:
            print 'Environment is being created from snapshot'

    def printFormattedCreateEmptyEnv(content):
        if content and content['successMessage']:
            print 'Empty environment is being created'

    class CreateController(controller.CementBaseController):

        class Meta:
            label = 'create'
            interface = controller.IController
            stacked_on = None
            description = "Create environment"
            arguments = [ ( ['-i', '--envId'], dict(dest='envId', help='environment id') ), 
            ( ['-c', '--envPolicyId'], dict(dest='envPolicyId', help='policy id') ), 
            ( ['-s', '--snapshotId'], dict(dest='snapshotId', help='snapshot id') ), 
            ( ['-n', '--newName'], dict(dest='newName', help='environment new name') ), 
            ( ['-d', '--description'], dict(dest='description', help='new environment description') ), 
            ( ['-showAll'], dict(dest='showAll', help='show all - use no filters', action='store_true') ), 
            ( ['-pn', '--projectName'], dict(dest='projectName', help='project name') ), 
            ( ['-p', '--projectFilter'], dict(dest='projectFilter', help='project name filter') ), 
            ( ['-b', '--blueprintFilter'], dict(dest='blueprintFilter', help='blueprint name filter') ), 
            ( ['-o', '--policyFilter'], dict(dest='policyFilter', help='environment policy name filter') ),
            ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options, default is RAWJSON') ),]

        @controller.expose(help="command under the create base namespace", hide=True)
        def default(self):
            print 'Available commands: env | empty | options'
        
        @controller.expose(help="Environment creation options")
        def options(self):
            projectFilter = getArg(self.pargs.projectFilter)
            blueprintFilter = getArg(self.pargs.blueprintFilter)
            policyFilter = getArg(self.pargs.policyFilter)
            
            if ( (self.pargs.projectFilter or self.pargs.blueprintFilter or self.pargs.policyFilter) and not self.pargs.showAll) or (self.pargs.showAll and not self.pargs.projectFilter and not self.pargs.blueprintFilter and not self.pargs.policyFilter):
                if self.pargs.showAll:
                    sendToOutput(api.create_ent_app_env_options('', '', ''), self.pargs, printFormattedCreateOptions)
                else:
                    sendToOutput(api.create_ent_app_env_options(projectFilter, blueprintFilter, policyFilter), self.pargs, printFormattedCreateOptions)
            else:
                print 'Usage: create options [-showAll] | [-p=<PROJECT_FILTER>] [-b=<BLUEPRINT_FILTER>] [-o=<ENVIRONMENT_POLICY_FILTER>]'
                
        @controller.expose(help="Create environment from an existing snapshot")
        def env(self):
            if self.pargs.envPolicyId and self.pargs.snapshotId:
                sendToOutput(api.create_ent_app_env(self.pargs.envPolicyId, self.pargs.snapshotId, getArg(self.pargs.newName), getArg(self.pargs.projectFilter), getArg(self.pargs.blueprintFilter), getArg(self.pargs.policyFilter)), self.pargs, printFormattedCreateEnv)
            else:
                print 'Usage: create env -c=<POLICY_ID> -s=<SNAPSHOT_ID> [-n=<ENV_NAME>] [-p=<PROJECT_FILTER>] [-b=<BLUEPRINT_FILTER>] [-o=<ENVIRONMENT_POLICY_FILTER>]'

        @controller.expose(help="Create an empty environment")
        def empty(self):
            description = getArg(self.pargs.description)
            
            if self.pargs.newName and self.pargs.projectName:
                sendToOutput(api.create_empty_ent_app_env(self.pargs.newName, self.pargs.projectName, description), self.pargs, printFormattedCreateEmptyEnv)
            else:
                print 'Usage: create empty -n=<ENV_NAME> -pn=<PROJECT_NAME> [-d=<DESCRIPTION>]'

    #======================================================================================================================================
    #== Login Controller
    #======================================================================================================================================         
    
    def printFormattedLoginGet(content):
        print content['login_url']
    
    class LoginController(controller.CementBaseController):

        class Meta:
            label = 'login'
            interface = controller.IController
            stacked_on = None
            description = "Login and manage your credentials"
            arguments = [ ( ['-u', '--url'], dict(dest='url', help='url to redirect to') ),
                        ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options, default is RAWJSON') ),]

        @controller.expose(help="command under the login base namespace", hide=True)
        def default(self):
            print 'Available commands: geturl'

        @controller.expose(help="Get a url that logs you automatically to CloudShare")
        def geturl(self):
            if self.pargs.url:
                sendToOutput(api.get_login_url(self.pargs.url), self.pargs, printFormattedLoginGet)
            else:
                print 'Usage: login geturl -u=<URL>'

        
    #======================================================================================================================================
    #== Snapshot Controller
    #======================================================================================================================================   
    
    def printFormattedSnapshotInfo(content):
        snapshot = cleanupDictionary(content)
        extraInfo = ''
        if snapshot['isDefault'] == True:
            extraInfo += ' [Default]'
        if snapshot['isLatest'] == True:
            extraInfo += ' [Latest]'

        print snapshot['snapshotId'] + ' - ' + snapshot['name'] + ' (' + snapshot['creationTime'] + ')' + extraInfo
        if snapshot['url'] and snapshot['url'] != '':
           print snapshot['url']
        print 'vms:'
        for vm in snapshot['machineList']:
            vm = cleanupDictionary(vm)
            print '    ' + vm['name'] + ' [CPUs:' + str(vm['cpu_count']) + ' Disk:' + str(vm['diskSize_mb']) + 'MB RAM:' + str(vm['memory_mb']) + 'MB]'
            
    def printFormattedSnapshotList(content):
        for snapshot in content:
            snapshot = cleanupDictionary(snapshot)
            extraInfo = ''
            if snapshot['IsDefault'] == True:
                extraInfo += ' [Default]'
            if snapshot['IsLatest'] == True:
                extraInfo += ' [Latest]'
                
            print snapshot['SnapshotId'] + ' - ' + snapshot['Name'] + ' (' + snapshot['CreationTime'] + ')' + extraInfo 
    
    def printFormattedSetDefault(content):
        if content and content['snapshotId']:
            print 'The snapshot is set to be default'
            
    class SnapshotController(controller.CementBaseController):

        class Meta:
            label = 'snapshot'
            interface = controller.IController
            stacked_on = None
            description = "Snapshots info and settings"
            arguments = [ ( ['-i', '--envId'], dict(dest='envId', help='environment id') ), 
            ( ['-s', '--snapshotId'], dict(dest='snapshotId', help='snapshot id') ),
            ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options, default is RAWJSON') ),]

        @controller.expose(help="command under the snapshot base namespace", hide=True)
        def default(self):
            print 'Available commands: list | info | setdefault'
        
        @controller.expose(help="List snapshots for a given environment")
        def list(self):
            
            if self.pargs.envId:
                sendToOutput(api.get_snapshots(self.pargs.envId), self.pargs, printFormattedSnapshotList)
            else:
                print 'Usage: snapshot list -i=<ENV_ID>'
                
        @controller.expose(help="Get snapshot info")
        def info(self):
            
            if self.pargs.snapshotId:
                sendToOutput(api.get_snapshot_info(self.pargs.snapshotId), self.pargs, printFormattedSnapshotInfo)
            else:
                print 'Usage: snapshot info -s=<SNAPSHOT_ID>'
                
        @controller.expose(help="Set snapshot as default for the blueprint")
        def setdefault(self):
            
            if self.pargs.envId and self.pargs.snapshotId:
                sendToOutput(api.mark_snapshot_default(self.pargs.envId, self.pargs.snapshotId), self.pargs, printFormattedSetDefault)
            else:
                print 'Usage: snapshot setdefault -i=<ENV_ID> -s=<SNAPSHOT_ID>'
                
    #======================================================================================================================================
    #== Create Snapshot Controller
    #======================================================================================================================================   
    def printFormattedCreateSnapshot(content):
        if content and content['envId']:
            print 'Snapshot is being created'

    def printFormattedBlueprints(content):
        for blueprint in content:
            blueprint = cleanupDictionary(blueprint)
            print blueprint['ApiId'] + ' - ' + blueprint['Name']
                
    class CreateSnapshotController(controller.CementBaseController):

        class Meta:
            label = 'createsnapshot'
            interface = controller.IController
            stacked_on = None
            description = "Create environment from a snapshot"
            arguments = [ ( ['-i', '--envId'], dict(dest='envId', help='environment id') ), 
            ( ['-n', '--snapshotName'], dict(dest='snapshotName', help='snapshot name') ),
            ( ['-bn', '--blueprintName'], dict(dest='blueprintName', help='new blueprint name') ),
            ( ['-b', '--blueprintId'], dict(dest='blueprintId', help='destination blueprint id') ),
            ( ['-d', '--description'], dict(dest='description', help='snapshot description') ),
            ( ['-s', '--snapshotId'], dict(dest='snapshotId', help='snapshot id') ),
            ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options, default is RAWJSON') ),
            ( ['-sd'], dict(dest='setDefault', help='set as default', action='store_true') ),]

        @controller.expose(help="command under the createsnapshot base namespace", hide=True)
        def default(self):
            print 'Available commands: create | new | add | listblueprints'
        
        @controller.expose(help="Take snapshot")
        def create(self):
        
            description = getArg(self.pargs.description)
            setAsDefault = self.pargs.setDefault
            
            if self.pargs.envId and self.pargs.snapshotName:
                sendToOutput(api.ent_app_take_snapshot(self.pargs.envId, self.pargs.snapshotName, self.pargs.description, setAsDefault), self.pargs, printFormattedCreateSnapshot)
            else:
                print 'Usage: createsnapshot create -i=<ENV_ID> -n=<SNAPSHOT_NAME> [-d=<SNAPSHOT_DESCRIPTION>] [-sd]'
                
        @controller.expose(help="Take snapshot into a new blueprint")
        def new(self):
        
            description = getArg(self.pargs.description)
            if self.pargs.envId and self.pargs.snapshotName and self.pargs.blueprintName:
                sendToOutput(api.ent_app_take_snapshot_to_new_blueprint(self.pargs.envId, self.pargs.snapshotName, self.pargs.blueprintName, description), self.pargs, printFormattedCreateSnapshot)
            else:
                print 'Usage: createsnapshot new -i=<ENV_ID> -n=<SNAPSHOT_NAME> -bn=<NEW_BLUEPRINT_NAME> [-d=<SNAPSHOT_DESCRIPTION>]'
                
        @controller.expose(help="Take snapshot into an existing blueprint")
        def add(self):
            
            description = getArg(self.pargs.description)
            setAsDefault = self.pargs.setDefault
            
            if self.pargs.envId and self.pargs.snapshotName and self.pargs.blueprintId:
                sendToOutput(api.ent_app_take_snapshot_to_existing_blueprint(self.pargs.envId, self.pargs.snapshotName, self.pargs.blueprintId, description, setAsDefault), self.pargs, printFormattedCreateSnapshot)
            else:
                print 'Usage: createsnapshot add -i=<ENV_ID> -n=<SNAPSHOT_NAME> -b=<DESTINATION_BLUEPRINT_ID> [-d=<SNAPSHOT_DESCRIPTION>] [-sd]'

        @controller.expose(help="Get blueprints list for taking snapshots to (information only)")
        def listblueprints(self):
            if self.pargs.envId:
                sendToOutput(api.get_blueprints_for_publish(self.pargs.envId), self.pargs, printFormattedBlueprints)
            else:
                print 'Usage: createsnapshot listblueprints -i=<ENV_ID>'
    #======================================================================================================================================
    #== RDP Controller
    #======================================================================================================================================         
    class RDPController(controller.CementBaseController):

        class Meta:
            label = 'rdp'
            interface = controller.IController
            stacked_on = None
            description = "RDP connection to VMs"
            arguments = [ ( ['-i', '--envId'], dict(dest='envId', help='environment id') ), 
            ( ['-v', '--vmId'], dict(dest='vmId', help='virtual machine id') ),
            ( ['-c'], dict(dest='console', help='is console connection', action='store_true') ),
            ( ['-dw', '--width'], dict(dest='width', help='desktop width') ),
            ( ['-dh', '--height'], dict(dest='height', help='desktop height') ),
            ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options, default is RAWJSON') ),]

        @controller.expose(help="command under the rdp base namespace", hide=True)
        def default(self):
            print 'Available commands: connect'

        @controller.expose(help="Connect to your vm using RDP")
        def connect(self):
            
            isConsole = self.pargs.console
            desktopWidth = getArg(self.pargs.width)
            desktopHeight = getArg(self.pargs.height)
            
            if self.pargs.envId and self.pargs.vmId:
                data = api.get_remote_access(self.pargs.envId, self.pargs.vmId, isConsole, desktopWidth, desktopHeight)
                rdpConnect(data)
            else:
                print 'Usage: rdp connect -i=<ENV_ID> -v=<VM_ID> [-c] [-dw=<WIDTH>] [-dh=<HEIGHT>]'
    
    #======================================================================================================================================
    #== Config Controller
    #======================================================================================================================================         
    class ConfigController(controller.CementBaseController):

        class Meta:
            label = 'config'
            interface = controller.IController
            stacked_on = None
            description = "Configuration settings edit"
            arguments = [ ( ['-i', '--apiId'], dict(dest='apiId', help='API_ID') ),
                        ( ['-k', '--apiKey'], dict(dest='apiKey', help='API_KEY') ),
                        ( ['-s', '--server'], dict(dest='server', help='API_SERVER') ),]
            

        @controller.expose(help="command under the config base namespace", hide=True)
        def default(self):
            print 'Available commands: setserver | setcredentials'

        @controller.expose(help="Change API credentials on config file")
        def setcredentials(self):
            if self.pargs.apiId and self.pargs.apiKey:
                confFileName = getConfigFile()
                f = open(confFileName, 'r')
                
                conf = f.readlines()
                f.close()
                
                for (i, line) in enumerate(conf):
                    if line.find('userapiid') != -1:
                        conf[i] = 'userapiid = ' + self.pargs.apiId + '\n'
                    if line.find('userapikey') != -1:
                        conf[i] = 'userapikey = ' + self.pargs.apiKey + '\n'

                f = open(confFileName, 'w')
                for line in conf:
                    f.write(line)
                    
                f.close()
                print 'Credentials were changed'
            else:
                print 'Usage: config setcredentials -i=<API_ID> -k=<API_KEY>'
                
        @controller.expose(help="Change API host on config file")
        def setserver(self):
            if self.pargs.server:
                confFileName = getConfigFile()
                f = open(confFileName, 'r')
                
                conf = f.readlines()
                f.close()
                
                for (i, line) in enumerate(conf):
                    if line.find('host') != -1:
                        conf[i] = 'host = ' + self.pargs.server + '\n'

                f = open(confFileName, 'w')
                for line in conf:
                    f.write(line)
                    
                f.close()
                print 'Server was changed'
            else:
                print 'Usage: config setserver -s=<API_SERVER>'
                
    #======================================================================================================================================
    #== MAIN
    #======================================================================================================================================
    
    app = foundation.CementApp('cloudshare', config_files=[getConfigFile()], base_controller = MyAppBaseController)
    
    try:
        # Register all controllers
        handler.register(EnvController)
        handler.register(InfoController)
        handler.register(CreateController)
        handler.register(VmController)
        handler.register(CloudfoldersController)
        handler.register(TemplateController)
        handler.register(LoginController)
        handler.register(SnapshotController)
        handler.register(CreateSnapshotController)
        handler.register(RDPController)
        handler.register(ConfigController)

        app.setup()
        
        if app.config.has_section('credentials') and app.config.has_key('credentials', 'userapiid') and app.config.has_key('credentials', 'userapikey'):
        
            apiId = app.config.get_section_dict('credentials')['userapiid']
            apiKey = app.config.get_section_dict('credentials')['userapikey']
            
            if app.config.has_section('environment') and app.config.has_key('environment', 'host') and app.config.has_key('environment', 'version'):
                host = app.config.get_section_dict('environment')['host']
                version = app.config.get_section_dict('environment')['version']
                
                if host == '':
                    sys.stderr.write('Missing environment arguments in configuration file `' + getConfigFile() + '`, you can change server using: \ncloudshare config setserver -s=<API_SERVER>\n\n')
                    api = CSHighApi('', '', 'v2', 'use.cloudshare.com')

            if apiId == '' or apiKey == '':
                sys.stderr.write('Missing values for credentials in `' + getConfigFile() + '`, you can add credentials using: \ncloudshare config setcredentials -i=<API_ID> -k=<API_KEY>\n\n')
                api = CSHighApi('', '', 'v2', 'use.cloudshare.com')
            else:
                api = CSHighApi(apiId, apiKey, version, host)
        else:
            sys.stderr.write('Missing credentials in `' + getConfigFile() + '`, you can edit credentials using: \ncloudshare config setcredentials -i=<API_ID> -k=<API_KEY>\n\n')
            api = CSHighApi('', '', 'v2', 'use.cloudshare.com')
            
        app.run()
        
    finally:
        app.close()

if __name__ == '__main__':
    main()

