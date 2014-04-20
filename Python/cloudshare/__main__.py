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
        
        if app.config.has_section('output') and 'type' in app.config.keys('output'):
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
        return module_path() + '/config.conf'
    
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
            interface = controller.IController
            description = "CloudShare API client"
            arguments = [ ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options (RAWJSON | FORMATTED)') ), ]

        @controller.expose(hide=True, aliases=['run'])
        def default(self):
            print 'Available commands: info | env | vm | create | snapshot | createsnapshot | tmpl | cf | login | rdp | config'
            
    #======================================================================================================================================
    #== Info Controller
    #====================================================================================================================================== 
    
    def printFormattedList(content):
        for env in content:
            hasProject = env['project'] != None
            env = cleanupDictionary(env)
            if hasProject:
                print env['envId'] + ' - ' + env['name'] + ' of ' + env['project'] + ' (' + env['status_text'] + ')'
            else:
                print env['envId'] + ' - ' + env['name'] + ' (' + env['status_text'] + ')'
                
    def printFormattedState(content):
        content = cleanupDictionary(content)
        print content['envId'] + ' - ' + content['name'] + ' (' + content['status_text'] + ')'
        print 'vms:'
        for vm in content['vms']:
            vm = cleanupDictionary(vm)
            status = vm['status_text']
            if status == 'In progress' and vm['progress']:
                status = str(vm['progress']) + '%'
            print '    ' + vm['id'] + ' - ' + vm['name'] + ' (' + status + ')'
     
    class InfoController(controller.CementBaseController):

        class Meta:
            label = 'info'
            interface = controller.IController
            stacked_on = 'base'
            stacked_type = 'nested'
            description = "Entities Information"
            arguments = [ ( ['-i', '--env-id'], dict(dest='envId', help='environment id') ),
                          ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options(RAWJSON | FORMATTED)') ),]

        @controller.expose(help="command under the info base namespace", hide=True)
        def default(self):
            print 'Available commands: list | state | projectslist'
        
        @controller.expose(help="List your environments")
        def list(self):
            sendToOutput(api.list_environments(), self.app.pargs, printFormattedList)
            
        @controller.expose(help="Get environment state")
        def state(self):
            
            if self.app.pargs.envId:
                sendToOutput(api.get_environment_status(self.app.pargs.envId), self.app.pargs, printFormattedState)
            else:
                print 'Usage: info state -i=<ENV_ID>'

        @controller.expose(help="Get projects list")
        def projectslist(self):
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

    def printFormattedEnvPostpone(content):
        if content and content['is_success'] and content['message']:
            print 'Environment will be suspended in ' + content['message'] + ' minutes'
            
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
            stacked_on = 'base'
            stacked_type = 'nested'
            description = "Environment Management"
            arguments = [ ( ['-i', '--env-id'], dict(dest='envId', help='environment id') ), ( ['-s', '--snapshot-id'], dict(dest='snapshotId', help='snapshot id') ),
                        ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options(RAWJSON | FORMATTED)') ),
                        ( ['-c'], dict(dest='noConfirm', help='no confirmations', action='store_true') ),]

        @controller.expose(help="command under the env base namespace", hide=True)
        def default(self):
            print 'Available commands: resume | suspend | extend | postpone | revert | revertto | delete'
        
        @controller.expose(help="Resume environment")
        def resume(self):
            if self.app.pargs.envId:
                sendToOutput(api.resume_environment(self.app.pargs.envId), self.app.pargs, printFormattedEnvResume)
            else:
                print 'Usage: env resume -i=<ENV_ID>'

        @controller.expose(help="Suspend environment")
        def suspend(self):
            if self.app.pargs.envId:
                sendToOutput(api.suspend_environment(self.app.pargs.envId), self.app.pargs, printFormattedEnvSuspend)
            else:
                print 'Usage: env suspend -i=<ENV_ID>'

        @controller.expose(help="Extend environment time")
        def extend(self):
            if self.app.pargs.envId:
                sendToOutput(api.extend_environment(self.app.pargs.envId), self.app.pargs, printFormattedEnvExtend)
            else:
                print 'Usage: env extend -i=<ENV_ID>'
                
        @controller.expose(help="Postpone environment suspend time")
        def postpone(self):
            if self.app.pargs.envId:
                sendToOutput(api.postpone_inactivity(self.app.pargs.envId), self.app.pargs, printFormattedEnvPostpone)
            else:
                print 'Usage: env postpone -i=<ENV_ID>'

        @controller.expose(help="Revert environment")
        def revert(self):
            if self.app.pargs.envId:
                if self.app.pargs.noConfirm or areYouSure('revert this environment'):
                    sendToOutput(api.revert_environment(self.app.pargs.envId), self.app.pargs, printFormattedEnvRevert)
            else:
                print 'Usage: env revert -i=<ENV_ID> [-c]'

        @controller.expose(help="Revert environment into a specific snapshot")
        def revertto(self):
            if self.app.pargs.envId and self.app.pargs.snapshotId:
                if self.app.pargs.noConfirm or areYouSure('revert this environment'):
                    sendToOutput(api.revert_environment_to_snapshot(self.app.pargs.envId, self.app.pargs.snapshotId), self.app.pargs, printFormattedEnvRevert)
            else:
                print 'Usage: env revertto -i=<ENV_ID> -s=<SNAPSHOT_ID> [-c]'

        @controller.expose(help="Delete environment")
        def delete(self):
            if self.app.pargs.envId:
                if self.app.pargs.noConfirm or areYouSure('delete this environment'):
                    sendToOutput(api.delete_environment(self.app.pargs.envId), self.app.pargs, printFormattedEnvDelete)
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
        if content and content['executionId']:
            print 'Script is being executed on VM'

    def printFormattedEditHw(content):
        if content:
            print "VM's hardware is being updated"
        if content['conflictsFound']:
            print 'Warning: CloudShare is now handling a conflicting edit hardware change. Conflicting resources:\n'
            print ','.join(content['conflicts'])
            
    def printFormattedVmCheckExecId(content):
        if content:
            if content['success'] != None:
                if content['success'] == True:
                    print 'Execution was successful'
                else:
                    print 'Execution failed'
            else:
                print 'no execution success result yet'

            if content['error_code']:
                print 'exit code:' + content['error_code']
            else:
                print 'no exit code yet'
            
            if content['standard_output']:
                print 'stdout:' + content['standard_output']
            else:
                print 'no stdout'

            if content['standard_error']:
                print 'stderr:' + content['standard_error']
            else:
                print 'no stderr'
            
    class VmController(controller.CementBaseController):

        class Meta:
            label = 'vm'
            interface = controller.IController
            stacked_on = 'base'
            stacked_type = 'nested'
            description = "Manage your VMs"
            arguments = [ ( ['-i', '--env-id'], dict(dest='envId', help='environment id') ), 
                        ( ['-v', '--vm-id'],    dict(dest='vmId', help='virtual machine id') ),
                        ( ['-s', '--script-path'], dict(dest='scriptPath', help='script path') ),
                        ( ['-e', '--exec-id'], dict(dest='execId', help='execution id') ),
                        ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options(RAWJSON | FORMATTED)') ),
                        ( ['-c'], dict(dest='noConfirm', help='no confirmations', action='store_true') ),
                        ( ['-n', '--num-cpus'],    dict(dest='numCpus', help='num requested cpus') ),
                        ( ['-r', '--mb-ram'], dict(dest='mbRam', help='amount of requested ram') ),
                        ( ['-d', '--gb-disk'], dict(dest='gbDisk', help='amount of requested disk') ),

                        ]

        @controller.expose(help="command under the vm base namespace", hide=True)
        def default(self):
            print 'Available commands: delete | revert | reboot | execute | checkexecute | edithw'
        
        @controller.expose(help="Delete vm")
        def delete(self):
            if self.app.pargs.envId and self.app.pargs.vmId:
                if self.app.pargs.noConfirm or areYouSure('delete this vm'):
                    sendToOutput(api.delete_vm(self.app.pargs.envId, self.app.pargs.vmId), self.app.pargs, printFormattedVmDelete)
            else:
                print 'Usage: vm delete -i=<ENV_ID> -v=<VM_ID> [-c]'

        @controller.expose(help="Revert vm")
        def revert(self):
            if self.app.pargs.envId and self.app.pargs.vmId:
                sendToOutput(api.revert_vm(self.app.pargs.envId, self.app.pargs.vmId), self.app.pargs, printFormattedVmRevert)
            else:
                print 'Usage: vm revert -i=<ENV_ID> -v=<VM_ID>'
                
        @controller.expose(help="Reboot vm")
        def reboot(self):
            if self.app.pargs.envId and self.app.pargs.vmId:
                sendToOutput(api.reboot_vm(self.app.pargs.envId, self.app.pargs.vmId), self.app.pargs, printFormattedVmReboot)
            else:
                print 'Usage: vm reboot -i=<ENV_ID> -v=<VM_ID>'
        
        @controller.expose(help="Edits the hardware of the machine")
        def edithw(self):
            if self.app.pargs.envId and self.app.pargs.vmId:
                sendToOutput(api.edit_machine_hardware(self.app.pargs.envId, self.app.pargs.vmId, self.app.pargs.numCpus, self.app.pargs.mbRam, self.app.pargs.gbDisk)
                    , self.app.pargs, printFormattedEditHw)
            else:
                print 'Usage: vm execute -i=<ENV_ID> -v=<VM_ID> [-n=<NUM_CPUS>] [-r=<MB_RAM>] [-d=<GB_DISK>]'

        @controller.expose(help="Execute script on vm")
        def execute(self):
            if self.app.pargs.envId and self.app.pargs.vmId and self.app.pargs.scriptPath:
                sendToOutput(api.execute_path(self.app.pargs.envId, self.app.pargs.vmId, self.app.pargs.scriptPath), self.app.pargs, printFormattedVmExecPath)
            else:
                print 'Usage: vm execute -i=<ENV_ID> -v=<VM_ID> -s=<SCRIPT_PATH>'
                
        @controller.expose(help="Check execution status of a script")
        def checkexecute(self):
            if self.app.pargs.envId and self.app.pargs.vmId and self.app.pargs.execId:
                sendToOutput(api.check_execution_id(self.app.pargs.envId, self.app.pargs.vmId, self.app.pargs.execId), self.app.pargs, printFormattedVmCheckExecId)
            else:
                print 'Usage: vm checkexecute -i=<ENV_ID> -v=<VM_ID> -e=<EXECUTION_ID>'

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
            
    def printFormattedRegeneratePassword(content):
        if content and content['new_password']:
            print 'CloudFolder password was changed and it is now \'' + content['new_password'] + '\''
            
    class CloudfoldersController(controller.CementBaseController):

        class Meta:
            label = 'cf'
            interface = controller.IController
            stacked_on = 'base'
            stacked_type = 'nested'
            description = "Cloud folders actions"
            arguments = [ ( ['-i', '--env-id'], dict(dest='envId', help='environment id') ), ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options(RAWJSON | FORMATTED)') ),]

        @controller.expose(help="command under the cf base namespace", hide=True)
        def default(self):
            print 'Available commands: info | mount | unmount | mountext | passwordregen'
        
        @controller.expose(help="CloudFolders info")
        def info(self):
            sendToOutput(api.get_cloudfolders_info(), self.app.pargs, printFormattedCloudFoldersInfo)

        @controller.expose(help="Mount environment")
        def mount(self):
            if self.app.pargs.envId:
                sendToOutput(api.mount(self.app.pargs.envId), self.app.pargs, printFormattedCfMount)
            else:
                print 'Usage: cf mount -i=<ENV_ID>'
                
        @controller.expose(help="Unmount environment")
        def unmount(self):
            if self.app.pargs.envId:
                sendToOutput(api.unmount(self.app.pargs.envId), self.app.pargs, printFormattedCfUnmount)
            else:
                print 'Usage: cf unmount -i=<ENV_ID>'
                
        @controller.expose(help="Mount environment, and fetch additional info")
        def mountext(self):
            if self.app.pargs.envId:
                sendToOutput(api.mount_and_fetch_info_ext(self.app.pargs.envId), self.app.pargs, printFormattedCloudFoldersMountExt)
            else:
                print 'Usage: cf mountext -i=<ENV_ID>'
                
        @controller.expose(help="Regenerate CloudFolders password")
        def passwordregen(self):
            sendToOutput(api.regenerate_cloudfolders_password(), self.app.pargs, printFormattedRegeneratePassword)
                
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
            stacked_on = 'base'
            stacked_type = 'nested'
            description = "Templates actions"
            arguments = [ ( ['-i', '--env-id'], dict(dest='envId', help='environment id') ),
                        ( ['-t', '--tmpl-id'], dict(dest='tmplId', help='template id') ),
                        ( ['-n', '--new-vm-name'], dict(dest='newVmName', help='new vm name') ),
                        ( ['-d', '--description'], dict(dest='description', help='new vm description') ),
                        ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options(RAWJSON | FORMATTED)') )]

        @controller.expose(help="command under the tmpl base namespace", hide=True)
        def default(self):
            print 'Available commands: list | add'

        @controller.expose(help="List available templates")
        def list(self):
            sendToOutput(api.list_templates(), self.app.pargs, printFormattedTmplList)

        @controller.expose(help="Add a vm to an existing environment based on a given template")
        def add(self):
            description = getArg(self.app.pargs.description)
            if self.app.pargs.envId and self.app.pargs.tmplId and self.app.pargs.newVmName:
                sendToOutput(api.add_vm_from_template(self.app.pargs.envId, self.app.pargs.tmplId, self.app.pargs.newVmName, description), self.app.pargs, printFormattedTmplAddToEnv)
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
            stacked_on = 'base'
            stacked_type = 'nested'
            description = "Create environment"
            arguments = [ ( ['-i', '--env-id'], dict(dest='envId', help='environment id') ), 
            ( ['-c', '--env-policy-id'], dict(dest='envPolicyId', help='policy id') ), 
            ( ['-s', '--snapshot-id'], dict(dest='snapshotId', help='snapshot id') ), 
            ( ['-n', '--new-name'], dict(dest='newName', help='environment new name') ), 
            ( ['-d', '--description'], dict(dest='description', help='new environment description') ), 
            ( ['-showall'], dict(dest='showAll', help='show all - use no filters', action='store_true') ), 
            ( ['-pn', '--project-name'], dict(dest='projectName', help='project name') ), 
            ( ['-p', '--project-filter'], dict(dest='projectFilter', help='project name filter') ), 
            ( ['-b', '--blueprint-filter'], dict(dest='blueprintFilter', help='blueprint name filter') ), 
            ( ['-o', '--policy-filter'], dict(dest='policyFilter', help='environment policy name filter') ),
            ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options(RAWJSON | FORMATTED)') ),]

        @controller.expose(help="command under the create base namespace", hide=True)
        def default(self):
            print 'Available commands: env | empty | options'
        
        @controller.expose(help="Environment creation options")
        def options(self):
            projectFilter = getArg(self.app.pargs.projectFilter)
            blueprintFilter = getArg(self.app.pargs.blueprintFilter)
            policyFilter = getArg(self.app.pargs.policyFilter)
            
            if ( (self.app.pargs.projectFilter or self.app.pargs.blueprintFilter or self.app.pargs.policyFilter) and not self.app.pargs.showAll) or (self.app.pargs.showAll and not self.app.pargs.projectFilter and not self.app.pargs.blueprintFilter and not self.app.pargs.policyFilter):
                if self.app.pargs.showAll:
                    sendToOutput(api.create_ent_app_env_options('', '', ''), self.app.pargs, printFormattedCreateOptions)
                else:
                    sendToOutput(api.create_ent_app_env_options(projectFilter, blueprintFilter, policyFilter), self.app.pargs, printFormattedCreateOptions)
            else:
                print 'Usage: create options [-showall] | [-p=<PROJECT_FILTER>] [-b=<BLUEPRINT_FILTER>] [-o=<ENVIRONMENT_POLICY_FILTER>]'
                
        @controller.expose(help="Create environment from an existing snapshot")
        def env(self):
            if self.app.pargs.envPolicyId and self.app.pargs.snapshotId:
                sendToOutput(api.create_ent_app_env(self.app.pargs.envPolicyId, self.app.pargs.snapshotId, getArg(self.app.pargs.newName), getArg(self.app.pargs.projectFilter), getArg(self.app.pargs.blueprintFilter), getArg(self.app.pargs.policyFilter)), self.app.pargs, printFormattedCreateEnv)
            else:
                print 'Usage: create env -c=<POLICY_ID> -s=<SNAPSHOT_ID> [-n=<ENV_NAME>] [-p=<PROJECT_FILTER>] [-b=<BLUEPRINT_FILTER>] [-o=<ENVIRONMENT_POLICY_FILTER>]'

        @controller.expose(help="Create an empty environment")
        def empty(self):
            description = getArg(self.app.pargs.description)
            
            if self.app.pargs.newName and self.app.pargs.projectName:
                sendToOutput(api.create_empty_ent_app_env(self.app.pargs.newName, self.app.pargs.projectName, description), self.app.pargs, printFormattedCreateEmptyEnv)
            else:
                print 'Usage: create empty -n=<ENV_NAME> -pn=<PROJECT_NAME> [-d=<DESCRIPTION>]'

    #======================================================================================================================================
    #== Login Controller
    #======================================================================================================================================         
    
    def printFormattedLoginGet(content):
        print content['login_url']
    
    def printFormattedWhoAmI(content):
        if content:
            print 'User is ' + content['first_name'] + ' ' + content['last_name']
            print 'Email:' + content['email']
            print 'Phone:' + content['phone']
            print 'Company:' + content['company']
    
    class LoginController(controller.CementBaseController):

        class Meta:
            label = 'login'
            interface = controller.IController
            stacked_on = 'base'
            stacked_type = 'nested'
            description = "Login and manage your credentials"
            arguments = [ ( ['-u', '--url'], dict(dest='url', help='url to redirect to') ),
                        ( ['-ui', '--user-id'], dict(dest='userId', help='user API id') ),
                        ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options(RAWJSON | FORMATTED)') ),]

        @controller.expose(help="command under the login base namespace", hide=True)
        def default(self):
            print 'Available commands: geturl | whoami'

        @controller.expose(help="Get a url that logs you automatically to CloudShare")
        def geturl(self):
            if self.app.pargs.url:
                sendToOutput(api.get_login_url(self.app.pargs.url), self.app.pargs, printFormattedLoginGet)
            else:
                print 'Usage: login geturl -u=<URL>'

        @controller.expose(help="Get basic info about a user")
        def whoami(self):
            if self.app.pargs.userId:
                sendToOutput(api.who_am_i(self.app.pargs.userId), self.app.pargs, printFormattedWhoAmI)
            else:
                sendToOutput(api.who_am_i('IDENTITY'), self.app.pargs, printFormattedWhoAmI)
                
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
            stacked_on = 'base'
            stacked_type = 'nested'
            description = "Snapshots info and settings"
            arguments = [ ( ['-i', '--env-id'], dict(dest='envId', help='environment id') ), 
            ( ['-s', '--snapshot-id'], dict(dest='snapshotId', help='snapshot id') ),
            ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options(RAWJSON | FORMATTED)') ),]

        @controller.expose(help="command under the snapshot base namespace", hide=True)
        def default(self):
            print 'Available commands: list | info | setdefault'
        
        @controller.expose(help="List snapshots for a given environment")
        def list(self):
            
            if self.app.pargs.envId:
                sendToOutput(api.get_snapshots(self.app.pargs.envId), self.app.pargs, printFormattedSnapshotList)
            else:
                print 'Usage: snapshot list -i=<ENV_ID>'
                
        @controller.expose(help="Get snapshot info")
        def info(self):
            
            if self.app.pargs.snapshotId:
                sendToOutput(api.get_snapshot_info(self.app.pargs.snapshotId), self.app.pargs, printFormattedSnapshotInfo)
            else:
                print 'Usage: snapshot info -s=<SNAPSHOT_ID>'
                
        @controller.expose(help="Set snapshot as default for the blueprint")
        def setdefault(self):
            
            if self.app.pargs.envId and self.app.pargs.snapshotId:
                sendToOutput(api.mark_snapshot_default(self.app.pargs.envId, self.app.pargs.snapshotId), self.app.pargs, printFormattedSetDefault)
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
            stacked_on = 'base'
            stacked_type = 'nested'
            description = "Create snapshot actions"
            arguments = [ ( ['-i', '--env-id'], dict(dest='envId', help='environment id') ), 
            ( ['-n', '--snapshot-name'], dict(dest='snapshotName', help='snapshot name') ),
            ( ['-bn', '--blueprint-name'], dict(dest='blueprintName', help='new blueprint name') ),
            ( ['-b', '--blueprint-id'], dict(dest='blueprintId', help='destination blueprint id') ),
            ( ['-d', '--description'], dict(dest='description', help='snapshot description') ),
            ( ['-s', '--snapshot-id'], dict(dest='snapshotId', help='snapshot id') ),
            ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options(RAWJSON | FORMATTED)') ),
            ( ['-sd'], dict(dest='setDefault', help='set as default', action='store_true') ),]

        @controller.expose(help="command under the createsnapshot base namespace", hide=True)
        def default(self):
            print 'Available commands: create | new | add | listblueprints'
        
        @controller.expose(help="Take snapshot")
        def create(self):
        
            description = getArg(self.app.pargs.description)
            setAsDefault = self.app.pargs.setDefault
            
            if self.app.pargs.envId and self.app.pargs.snapshotName:
                sendToOutput(api.ent_app_take_snapshot(self.app.pargs.envId, self.app.pargs.snapshotName, self.app.pargs.description, setAsDefault), self.app.pargs, printFormattedCreateSnapshot)
            else:
                print 'Usage: createsnapshot create -i=<ENV_ID> -n=<SNAPSHOT_NAME> [-d=<SNAPSHOT_DESCRIPTION>] [-sd]'
                
        @controller.expose(help="Take snapshot into a new blueprint")
        def new(self):
        
            description = getArg(self.app.pargs.description)
            if self.app.pargs.envId and self.app.pargs.snapshotName and self.app.pargs.blueprintName:
                sendToOutput(api.ent_app_take_snapshot_to_new_blueprint(self.app.pargs.envId, self.app.pargs.snapshotName, self.app.pargs.blueprintName, description), self.app.pargs, printFormattedCreateSnapshot)
            else:
                print 'Usage: createsnapshot new -i=<ENV_ID> -n=<SNAPSHOT_NAME> -bn=<NEW_BLUEPRINT_NAME> [-d=<SNAPSHOT_DESCRIPTION>]'
                
        @controller.expose(help="Take snapshot into an existing blueprint")
        def add(self):
            
            description = getArg(self.app.pargs.description)
            setAsDefault = self.app.pargs.setDefault
            
            if self.app.pargs.envId and self.app.pargs.snapshotName and self.app.pargs.blueprintId:
                sendToOutput(api.ent_app_take_snapshot_to_existing_blueprint(self.app.pargs.envId, self.app.pargs.snapshotName, self.app.pargs.blueprintId, description, setAsDefault), self.app.pargs, printFormattedCreateSnapshot)
            else:
                print 'Usage: createsnapshot add -i=<ENV_ID> -n=<SNAPSHOT_NAME> -b=<DESTINATION_BLUEPRINT_ID> [-d=<SNAPSHOT_DESCRIPTION>] [-sd]'

        @controller.expose(help="Get blueprints list for taking snapshots to (information only)")
        def listblueprints(self):
            if self.app.pargs.envId:
                sendToOutput(api.get_blueprints_for_publish(self.app.pargs.envId), self.app.pargs, printFormattedBlueprints)
            else:
                print 'Usage: createsnapshot listblueprints -i=<ENV_ID>'
    #======================================================================================================================================
    #== RDP Controller
    #======================================================================================================================================         
    class RDPController(controller.CementBaseController):

        class Meta:
            label = 'rdp'
            interface = controller.IController
            stacked_on = 'base'
            stacked_type = 'nested'
            description = "RDP connection to VMs"
            arguments = [ ( ['-i', '--env-id'], dict(dest='envId', help='environment id') ), 
            ( ['-v', '--vm-id'], dict(dest='vmId', help='virtual machine id') ),
            ( ['-c'], dict(dest='console', help='is console connection', action='store_true') ),
            ( ['-dw', '--width'], dict(dest='width', help='desktop width') ),
            ( ['-dh', '--height'], dict(dest='height', help='desktop height') ),
            ( ['-f', '--formatting'], dict(dest='formatting', help='Output formatting options(RAWJSON | FORMATTED)') ),]

        @controller.expose(help="command under the rdp base namespace", hide=True)
        def default(self):
            print 'Available commands: connect'

        @controller.expose(help="Connect to your vm using RDP")
        def connect(self):
            
            isConsole = self.app.pargs.console
            desktopWidth = getArg(self.app.pargs.width)
            desktopHeight = getArg(self.app.pargs.height)
            
            if self.app.pargs.envId and self.app.pargs.vmId:
                data = api.get_remote_access(self.app.pargs.envId, self.app.pargs.vmId, isConsole, desktopWidth, desktopHeight)
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
            stacked_on = 'base'
            stacked_type = 'nested'
            description = "Configuration settings edit"
            arguments = [ ( ['-i', '--api-id'], dict(dest='apiId', help='API_ID') ),
                        ( ['-k', '--api-key'], dict(dest='apiKey', help='API_KEY') ),
                        ( ['-s', '--server'], dict(dest='server', help='API_SERVER') ),]
            

        @controller.expose(help="command under the config base namespace", hide=True)
        def default(self):
            print 'Available commands: setserver | setcredentials'

        @controller.expose(help="Change API credentials on config file")
        def setcredentials(self):
            if self.app.pargs.apiId and self.app.pargs.apiKey:
                confFileName = getConfigFile()
                f = open(confFileName, 'r')
                
                conf = f.readlines()
                f.close()
                
                for (i, line) in enumerate(conf):
                    if line.find('userapiid') != -1:
                        conf[i] = 'userapiid = ' + self.app.pargs.apiId + '\n'
                    if line.find('userapikey') != -1:
                        conf[i] = 'userapikey = ' + self.app.pargs.apiKey + '\n'

                f = open(confFileName, 'w')
                for line in conf:
                    f.write(line)
                    
                f.close()
                print 'Credentials were changed'
            else:
                print 'Usage: config setcredentials -i=<API_ID> -k=<API_KEY>'
                
        @controller.expose(help="Change API host on config file")
        def setserver(self):
            if self.app.pargs.server:
                confFileName = getConfigFile()
                f = open(confFileName, 'r')
                
                conf = f.readlines()
                f.close()
                
                for (i, line) in enumerate(conf):
                    if line.find('host') != -1:
                        conf[i] = 'host = ' + self.app.pargs.server + '\n'

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
        
        if app.config.has_section('credentials') and 'userapiid' in app.config.keys('credentials') and 'userapikey' in app.config.keys('credentials'):
        
            apiId = app.config.get_section_dict('credentials')['userapiid']
            apiKey = app.config.get_section_dict('credentials')['userapikey']
            
            if app.config.has_section('environment') and 'host' in app.config.keys('environment') and 'version' in app.config.keys('environment'):
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
        try: 
            app.run()
        except ApiException as p:
            sys.stderr.write("API Call returned an error\n")
            error_details = json.loads(p.content.decode('utf-8'))
            sys.stderr.write("status_text = " +  error_details["status_text"] + '\n')
            sys.stderr.write("status_code = " + error_details["status_code"] + '\n')
            raise
    finally:
        app.close()

if __name__ == '__main__':
    main()

