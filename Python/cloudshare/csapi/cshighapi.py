from .cslowapi import CSLowApi

class CSHighApi (object):

    def __init__(self, id, key, version=CSLowApi.DEFAULT_VERSION, host=CSLowApi.DEFAULT_HOST):
        self.lowapi = CSLowApi(id, key, version, host)

    def call(self, category, command, **params):
        return self.lowapi.call(category, command, **params).json()['data']
        
    # Env info

    def list_environments(self):
        return self.call('env', 'ListEnvironments')

    def list_environments_with_state(self):
        return self.call('env', 'ListEnvironmentsWithStateExt')

    def get_environment_status(self, envId):
        return self.call('env', 'GetEnvironmentStateExt', EnvId=envId)

    def get_environment_status_list(self):
        envs = self.list_environments()
        return [self.get_environment_status(env['envId']) for env in envs]

    # General env actions

    def resume_environment(self, envId):
        return self.call('env', 'ResumeEnvironment', EnvId=envId)

    def revert_environment(self, envId):
        return self.call('env', 'RevertEnvironment', EnvId=envId)

    def delete_environment(self, envId):
        return self.call('env', 'DeleteEnvironment', EnvId=envId)

    def extend_environment(self, envId):
        return self.call('env', 'ExtendEnvironment', EnvId=envId)
        
    def postpone_inactivity(self, envId):
        return self.call('env', 'PostponeInactivityAction', EnvId=envId)
    
    def suspend_environment(self, envId):
        return self.call('env', 'SuspendEnvironment', EnvId=envId)

    def revert_environment_to_snapshot(self, envId, snapshotId):
        return self.call('env', 'RevertEnvironmentToSnapshot', EnvId=envId, SnapshotId=snapshotId)

    # Create env actions

    def list_templates(self):
        return self.call('env', 'ListTemplates')

    def add_vm_from_template(self, envId, templateId, vm_name, vm_description):
        return self.call('env', 'AddVmFromTemplate', EnvId=envId, TemplateVmId=templateId, VmName=vm_name, VmDescription=vm_description)

    def create_ent_app_env_options(self, project_filter='', blueprint_filter='', env_policy_duration_filter=''):
        return self.call('env', 'CreateEntAppEnvOptions', ProjectFilter=project_filter, 
                                                          BlueprintFilter=blueprint_filter,
                                                          EnvironmentPolicyDurationFilter=env_policy_duration_filter)

    def create_ent_app_env(self, envPolicyId, snapshotId, env_new_name=None, project_filter='', blueprint_filter='', env_policy_duration_filter=''):
        return self.call('env', 'CreateEntAppEnv', EnvironmentPolicyId=envPolicyId,
                                                   SnapshotId=snapshotId,
                                                   ProjectFilter=project_filter,
                                                   BlueprintFilter=blueprint_filter,
                                                   EnvironmentPolicyDurationFilter=env_policy_duration_filter,
                                                   EnvironmentNewName=env_new_name)

    def create_empty_ent_app_env(self, env_name, project_name, description='none'):
        return self.call('env', 'CreateEmptyEntAppEnv', EnvName=env_name, ProjectName=project_name, Description=description)


    # Snapshots 
    
    def get_snapshots(self, envId):
        return self.call('env', 'GetSnapshots', EnvId=envId)
        
    def get_snapshot_info(self, snapshotId):
        return self.call('env', 'GetSnapshotDetails', SnapshotId=snapshotId)

    def get_blueprints_for_publish(self, envId):
        return self.call('env', 'GetBlueprintsForPublish', EnvId=envId)

    def mark_snapshot_default(self, envId, snapshotId):
        return self.call('env', 'MarkSnapshotDefault', EnvId=envId, SnapshotId=snapshotId)

    def ent_app_take_snapshot(self, envId, snapshot_name, description='', set_as_default=True):
        return self.call('env', 'EntAppTakeSnapshot', EnvId=envId, SnapshotName=snapshot_name, Description=description, SetAsDefault='true' if set_as_default else 'false')

    def ent_app_take_snapshot_to_new_blueprint(self, envId, snapshot_name, new_blueprint_name, description=''):
        return self.call('env', 'EntAppTakeSnapshotToNewBlueprint', EnvId=envId, SnapshotName=snapshot_name, NewBlueprintName=new_blueprint_name, Description=description)

    def ent_app_take_snapshot_to_existing_blueprint(self, envId, snapshot_name, otherBlueprintId, description='', set_as_default=True):
        return self.call('env', 'EntAppTakeSnapshotToExistingBlueprint', EnvId=envId, 
                                                                  SnapshotName=snapshot_name, 
                                                                  OtherBlueprintId=otherBlueprintId, 
                                                                  Desctiption=description, 
                                                                  SetAsDefault='true' if set_as_default else 'false')

     # VM actions

    def delete_vm(self, envId, vmId):
        return self.call('env', 'DeleteVm', EnvId=envId, VmId=vmId)

    def revert_vm(self, envId, vmId):
        return self.call('env', 'RevertVm', EnvId=envId, VmId=vmId)

    def reboot_vm(self, envId, vmId):
        return self.call('env', 'RebootVm', EnvId=envId, VmId=vmId)
    
    def execute_path(self, envId, vmId, path):
        return self.call('env', 'ExecutePathExt', EnvId=envId, VmId=vmId, Path=path)

    def edit_machine_hardware(self, envId, vmId, numCpus=None,mbRAM=None, gbDisk=None):
        return self.call('env', 'EditMachineHardware', EnvId=envId, VmId=vmId, NumCpus=numCpus, MemorySizeMBs=mbRAM, DiskSizeGBs=gbDisk)

    def check_execution_id(self, envId, vmId, exec_id):
        return self.call('env', 'CheckExecutionStatus', EnvId=envId, VmId=vmId, ExecutionId=exec_id)    
        
     # CloudFolders

    def get_cloudfolders_info(self):
        return self.call('env', 'GetCloudFoldersInfo')

    def mount(self, envId):
        return self.call('env', 'Mount', EnvId=envId)

    def unmount(self, envId):
        return self.call('env', 'Unmount', EnvId=envId)
        
    def mount_and_fetch_info(self, envId):
        return self.call('env', 'MountAndFetchInfo', EnvId=envId)
        
    def mount_and_fetch_info_ext(self, envId):
        return self.call('env', 'MountAndFetchInfoExt', EnvId=envId)

    def regenerate_cloudfolders_password(self):
        return self.call('env', 'RegenerateCloudfoldersPassword')

    # Login

    def get_login_url(self, url):
        return self.call('env', 'GetLoginUrl', Url=url)
        
    def who_am_i(self, userId):
        return self.call('env', 'WhoAmI', UserId=userId)
        
    # RDP

    def get_remote_access(self, envId, vmId, isConsole='', desktopWidth='', desktopHeight=''):
        return self.call('env', 'GetRemoteAccessFile', EnvId=envId, VmId=vmId, IsConsole=isConsole, DesktopWidth=desktopWidth, DesktopHeight=desktopHeight)

    # Admin 
    
    def list_allowed_commands(self):
        return self.call('admin', 'ListAllowedCommands')

    # Training 
       
    def list_classes(self, project_filter=''):
		return self.call('admin', 'ListClasses', ProjectFilter=project_filter)
        
    def register_student(self, classId, email, firstName, lastName):
		return self.call('admin', 'RegisterStudent', ClassId=classId, Email=email, FirstName=firstName, LastName=lastName)

    def register_students(self, students):
		"""register students into a class 
			Args:
				students: a list of students i.e. [{'classId':'xxxxxxx', 'email':'john@cloudshare.com','firstName':'John',  'lastName':'Doe'}]
		"""
		all_results = list()
		for student in students:
			result = self.register_student(student['classId'], student['email'], student['firstName'], student['lastName'])
			all_results.append(result)
		return all_results
		
		
		
		
		