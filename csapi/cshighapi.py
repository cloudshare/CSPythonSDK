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
        return self.call('env', 'ListEnvironmentsWithState')

    def get_environment_status(self, env):
        return self.call('env', 'GetEnvironmentState', EnvId=env['envId'])

    def get_environment_status_list(self):
        envs = self.list_environments()
        return [self.get_environment_status(env) for env in envs]

    def get_snapshots(self, env):
        return self.call('env', 'GetSnapshots', EnvId=env['envId'])

    # General env actions

    def resume_environment(self, env):
        self.call('env', 'ResumeEnvironment', EnvId=env['envId'])

    def revert_environment(self, env):
        self.call('env', 'RevertEnvironment', EnvId=env['envId'])

    def delete_environment(self, env):
        self.call('env', 'DeleteEnvironment', EnvId=env['envId'])

    def extend_environment(self, env):
        self.call('env', 'ExtendEnvironment', EnvId=env['envId'])
    
    def suspend_environment(self, env):
        self.call('env', 'SuspendEnvironment', EnvId=env['envId'])

    def revert_environment_to_snapshot(self, env, snapshot):
        self.call('env', 'RevertEnvironmentToSnapshot', EnvId=env['envId'], SnapshotId=snapshot.SnapshotId)


    # Create env actions

    def list_templates(self):
        return self.call('env', 'ListTemplates')

    def add_vm_from_template(self, env, template, vm_name, vm_description):
        self.call('env', 'AddVmFromTemplate', EnvId=env['envId'], TemplateVmId=template['id'], VmName=vm_name, VmDescription=vm_description)

    def create_ent_app_env_options(self, project_filter='', blueprint_filter='', env_policy_duration_filter=''):
        return self.call('env', 'CreateEntAppEnvOptions', ProjectFilter=project_filter, 
                                                          BlueprintFilter=blueprint_filter,
                                                          EnvironmentPolicyDurationFilter=env_policy_duration_filter)

    def create_ent_app_env(self, env_policy, snapshot, env_new_name=None, project_filter='', blueprint_filter='', env_policy_duration_filter=''):
        return self.call('env', 'CreateEntAppEnv', EnvironmentPolicyId=env_policy.EnvironmentPolicyId,
                                                   SnapshotId=snapshot.SnapshotId,
                                                   ProjectFilter=project_filter,
                                                   BlueprintFilter=blueprint_filter,
                                                   EnvironmentPolicyDurationFilter=env_policy_duration_filter,
                                                   EnvironmentNewName=env_new_name)

    def create_empty_ent_app_env(self, env_name, project_name, description='none'):
        self.call('env', 'CreateEmptyEntAppEnv', EnvName=env_name, ProjectName=project_name, Description=description)


    # Snapshots 

    def get_blueprints_for_publish(self, env):
        return self.call('env', 'GetBlueprintsForPublish', EnvId=env['envId'])

    def mark_snapshot_default(self, env, snapshot):
        self.call('env', 'MarkSnapshotDefault', EnvId=env['envId'], SnapshotId=snaphot['SnapshotId'])

    def ent_app_take_snapshot(self, env, snapshot_name, description='', set_as_default=True):
        self.call('env', 'EntAppTakeSnapshot', EnvId=env['envId'], SnapshotName=snapshot_name, Description=description, SetAsDefault='true' if set_as_default else 'false')

    def ent_app_take_snapshot_to_new_blueprint(self, env, snapshot_name, new_blueprint_name, description=''):
        self.call('env', 'EntAppTakeSnapshotToNewBlueprint', EnvId=env['envId'], SnapshotName=snap, NewBlueprintName=new_blueprint_name, Description=description)

    def ent_app_take_snapshot_to_existing_blueprint(self, env, snapshot_name, other_blueprint, description='', set_as_default=True):
        self.call('env', 'EntAppTakeSnapshotToExistingBlueprint', EnvId=env['endId'], 
                                                                  SnapshotName=snapshot_name, 
                                                                  OtherBlueprintId=other_blueprint.ApiId, 
                                                                  Desctiption=description, 
                                                                  SetAsDefault='true' if set_as_default else 'false')

     # VM actions

    def delete_vm(self, env, vm):
        self.call('env', 'DeleteVm', EnvId=env['envId'], VmId=vm['vmId'])

    def revert_vm(self, env, vm):
        self.call('env', 'RevertVm', EnvId=env['envId'], VmId=vm['vmId'])

    def reboot_vm(self, env, vm):
        self.call('env', 'RebootVm', EnvId=env['envId'], VmId=vm['vmId'])


     # CloudFolders

    def get_cloudfolders_info(self):
        return self.call('env', 'GetCloudFoldersInfo')

    def mount(self, env):
        self.call('env', 'Mount', EnvId=env['envId'])

    def unmount(self, env):
        self.call('env', 'Unmount', EnvId=env['envId'])

     # Login

    def get_login_url(self, url):
        return self.call('env', 'GetLoginUrl', Url=url)

