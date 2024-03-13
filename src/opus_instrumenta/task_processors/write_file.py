import os
import json
import traceback
import copy
import hashlib
import stat

from magnum_opus.operarius import LoggerWrapper, TaskProcessor, KeyValueStore, Task, StatePersistence
from opus_adstator.file_io import get_file_size, calculate_file_checksum


class WriteFile(TaskProcessor):

    def __init__(self, kind: str='WriteFile', kind_versions: list=['v1',], supported_commands: list = list(), logger: LoggerWrapper = LoggerWrapper()):
        self.spec = dict()
        self.metadata = dict()
        super().__init__(kind, kind_versions, supported_commands, logger)

    def existing_file_requires_update(self, log_header: str='')->bool:
        file_exists = False
        raise_exception = False
        try:
            if os.path.exists(self.spec['targetfile']) is True:
                if os.path.isfile(self.spec['targetfile']) is True:
                    file_exists = True
                else:
                    self.log(message='Target file object "{}" exists but is NOT a file. Cannot proceed.'.format(self.spec['targetfile']), build_log_message_header=False, level='error', header=log_header)
                    raise_exception = True   
        except:
            self.log(message='EXCEPTION: {}'.format(traceback.format_exc()), build_log_message_header=False, level='error', header=log_header)
            self.log(message='Returning False (exception) - for now we will try to create the file', build_log_message_header=False, level='debug', header=log_header)
            return False
        
        if raise_exception is True:
            raise Exception('Target file object "{}" exists but is NOT a file. Cannot proceed.'.format(self.spec['targetfile']))

        action_if_exists = 'overwrite'
        if 'actioniffilealreadyexists' in self.spec:
            if self.spec['actioniffilealreadyexists'].lower() in ('overwrite', 'skip',):
                action_if_exists = self.spec['actioniffilealreadyexists'].lower()

        self.log(message='file_exists        : {}'.format(file_exists), build_log_message_header=False, level='debug', header=log_header)
        self.log(message='action_if_exists   : {}'.format(action_if_exists), build_log_message_header=False, level='debug', header=log_header)

        if file_exists is True and action_if_exists == 'overwrite':
            self.log(message='Returning True [1]', build_log_message_header=False, level='debug', header=log_header)
            return True
        elif file_exists is False:
            self.log(message='Returning True [2]', build_log_message_header=False, level='debug', header=log_header)
            return True

        file_checksum = calculate_file_checksum(file_path=os.path.exists(self.spec['targetfile']), checksum_algorithm='sha256')
        spec_data_checksum = hashlib.sha256(self.spec['data'].encode('utf-8')).hexdigest()
        
        self.log(message='file_checksum      : {}'.format(file_exists), build_log_message_header=False, level='debug', header=log_header)
        self.log(message='spec_data_checksum : {}'.format(action_if_exists), build_log_message_header=False, level='debug', header=log_header)

        if file_checksum != spec_data_checksum:
            self.log(message='Returning True [3]', build_log_message_header=False, level='debug', header=log_header)
            return True

        self.log(message='Returning False (default)', build_log_message_header=False, level='debug', header=log_header)
        return False

    def process_task(self, task: Task, command: str, context: str = 'default', key_value_store: KeyValueStore = KeyValueStore(), state_persistence: StatePersistence = StatePersistence()) -> KeyValueStore:
        log_header = self.format_log_header(task=task, command=command, context=context)
        self.log(message='PROCESSING START - Default Action Called - Redirect to process_task_create_action()', build_log_message_header=False, level='info', header=log_header)
        return self.process_task_create_action(
            task=task,
            command=command,
            context=context,
            key_value_store=key_value_store,
            state_persistence=state_persistence
        )
    
    def process_task_create_action(self, task: Task, command: str, context: str = 'default', key_value_store: KeyValueStore = KeyValueStore(), state_persistence: StatePersistence = StatePersistence()) -> KeyValueStore:
        """This task processor will download a file from a HTTP or HTTPS server.

        # Spec fields

        Root levels spec fields

        | Field                       | Type    | Required | In Versions | Description                                                                                                                                                               |
        |-----------------------------|:-------:|:--------:|:-----------:|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
        | `targetFile`                | str     | Yes      | v1          | Full path to a file                                                                                                                                                       |
        | `data`                      | str     | Yes      | v1          | The actual content of the file. Typically a `Value` or `Variable` reference will be used here                                                                             |
        | `actionIfFileAlreadyExists` | str     | No       | v1          | optional (default=overwrite). Allowed values: overwrite (write the data to the file anyway - overwriting any previous data), skip (leave the current file as is and skip) |
        | `fileMode`                  | str     | No       | v1          | optional (default=normal). Allowed values: normal (chmod 600) or executable (chmod 700)                                                                                   |
 
        Args:
            task: The `Task` of kind `ShellScript` version `v1` to process
            command: The command is ignored for ShellScript processing - any task of this kind will ALWAYS be processed regardless of the command.
            context: The context is ignored for ShellScript processing - any task of this kind will ALWAYS be processed regardless of the context.
            key_value_store: An instance of the `KeyValueStore`. If none is supplied, a new instance will be created.
            state_persistence: An implementation of `StatePersistence` that the task processor can use to retrieve previous copies of the `Task` manifest in order to determine the actions to be performed.

        Returns:
            An updated `KeyValueStore`.

            * `task.kind:task.task_id:command:context:FILE_PATH` - The full path to the file
            * `task.kind:task.task_id:command:context:WRITTEN` - Boolean, where a TRUE value means the file was processed.
            * `task.kind:task.task_id:command:context:EXECUTABLE` - Boolean value which will be TRUE if the file has been set as executable
            * `task.kind:task.task_id:command:context:SIZE` - The file size in BYTES
            * `task.kind:task.task_id:command:context:SHA256_CHECKSUM` - The calculated file checksum (SHA256)

        Raises:
            Exception: As determined by the processing logic.
        """
        self.spec = copy.deepcopy(task.spec)
        self.metadata = copy.deepcopy(task.metadata)
        new_key_value_store = KeyValueStore()
        new_key_value_store.store = copy.deepcopy(key_value_store.store)
        log_header = self.format_log_header(task=task, command=command, context=context)
        self.log(message='PROCESSING START - Create Action', build_log_message_header=False, level='info', header=log_header)
        self.log(message='   spec: {}'.format(json.dumps(self.spec)), build_log_message_header=False, level='debug', header=log_header)
        if '{}:{}:{}:{}:RESULT'.format(task.kind,task.task_id,command,context) in key_value_store.store is True:
            self.log(message='The task have already been processed and will now be ignored. The KeyValueStore will be returned unmodified.', build_log_message_header=False, level='warning', header=log_header)
            return new_key_value_store

        if self.existing_file_requires_update(log_header=log_header) is False:
            self.log(message='File already exists and checksums match - no update required.', build_log_message_header=False, level='info', header=log_header)
            return new_key_value_store
        
        try:
            os.unlink(self.spec['targetfile'])
            self.log(message='Previous file deleted', build_log_message_header=False, level='info', header=log_header)
        except:
            pass

        with open(self.spec['targetFile'], 'w') as f:
            f.write(self.spec['data'])

        is_executable = False
        if 'filemode' in self.spec:
            if self.spec['filemode'].lower().startswith('ex'):
                st = os.stat(self.spec['targetfile'])
                os.chmod(self.spec['targetfile'], st.st_mode | stat.S_IEXEC)
                is_executable = True

        new_key_value_store.save(key='{}:{}:{}:{}:FILE_PATH'.format(self.kind, task.task_id, command, context), value=self.spec['targetfile'])
        new_key_value_store.save(key='{}:{}:{}:{}:WRITTEN'.format(self.kind, task.task_id, command, context), value=True)
        new_key_value_store.save(key='{}:{}:{}:{}:EXECUTABLE'.format(self.kind, task.task_id, command, context), value=is_executable)
        new_key_value_store.save(key='{}:{}:{}:{}:SIZE'.format(self.kind, task.task_id, command, context), value=get_file_size(file_path=self.spec['targetfile']))
        new_key_value_store.save(key='{}:{}:{}:{}:SHA256_CHECKSUM'.format(self.kind, task.task_id, command, context), value=calculate_file_checksum(file_path=self.spec['targetfile'], checksum_algorithm='sha256'))

        self.spec = dict()
        self.metadata = dict()
        self.log(message='DONE', build_log_message_header=False, level='info', header=log_header)
        return new_key_value_store

    def process_task_delete_action(self, task: Task, command: str, context: str = 'default', key_value_store: KeyValueStore = KeyValueStore(), state_persistence: StatePersistence = StatePersistence()) -> KeyValueStore:
        """This task processor will download a file from a HTTP or HTTPS server.

        # Spec fields

        Root levels spec fields

        | Field                       | Type    | Required | In Versions | Description                                                                                                                                                               |
        |-----------------------------|:-------:|:--------:|:-----------:|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
        | `targetFile`                | str     | Yes      | v1          | Full path to a file                                                                                                                                                       |
        | `data`                      | str     | Yes      | v1          | The actual content of the file. Typically a `Value` or `Variable` reference will be used here                                                                             |
        | `actionIfFileAlreadyExists` | str     | No       | v1          | optional (default=overwrite). Allowed values: overwrite (write the data to the file anyway - overwriting any previous data), skip (leave the current file as is and skip) |
        | `fileMode`                  | str     | No       | v1          | optional (default=normal). Allowed values: normal (chmod 600) or executable (chmod 700)                                                                                   |
 
        Args:
            task: The `Task` of kind `ShellScript` version `v1` to process
            command: The command is ignored for ShellScript processing - any task of this kind will ALWAYS be processed regardless of the command.
            context: The context is ignored for ShellScript processing - any task of this kind will ALWAYS be processed regardless of the context.
            key_value_store: An instance of the `KeyValueStore`. If none is supplied, a new instance will be created.
            state_persistence: An implementation of `StatePersistence` that the task processor can use to retrieve previous copies of the `Task` manifest in order to determine the actions to be performed.

        Returns:
            An updated `KeyValueStore`.

            * `task.kind:task.task_id:command:context:FILE_PATH` - The full path to the file
            * `task.kind:task.task_id:command:context:DELETED` - Boolean, where a `True` value means the file was deleted successfully.

        Raises:
            Exception: As determined by the processing logic.
        """
        self.spec = copy.deepcopy(task.spec)
        self.metadata = copy.deepcopy(task.metadata)
        new_key_value_store = KeyValueStore()
        new_key_value_store.store = copy.deepcopy(key_value_store.store)
        log_header = self.format_log_header(task=task, command=command, context=context)
        self.log(message='PROCESSING START - Delete Action', build_log_message_header=False, level='info', header=log_header)
        self.log(message='   spec: {}'.format(json.dumps(self.spec)), build_log_message_header=False, level='debug', header=log_header)
        if '{}:{}:{}:{}:RESULT'.format(task.kind,task.task_id,command,context) in key_value_store.store is True:
            self.log(message='The task have already been processed and will now be ignored. The KeyValueStore will be returned unmodified.', build_log_message_header=False, level='warning', header=log_header)
            return new_key_value_store

        

        self.spec = dict()
        self.metadata = dict()
        self.log(message='DONE', build_log_message_header=False, level='info', header=log_header)
        return new_key_value_store
    
    def process_task_describe_action(self, task: Task, command: str, context: str = 'default', key_value_store: KeyValueStore = KeyValueStore(), state_persistence: StatePersistence = StatePersistence()) -> KeyValueStore:
        """This task processor will download a file from a HTTP or HTTPS server.

        # Spec fields

        Root levels spec fields

        | Field                       | Type    | Required | In Versions | Description                                                                                                                                                               |
        |-----------------------------|:-------:|:--------:|:-----------:|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
        | `targetFile`                | str     | Yes      | v1          | Full path to a file                                                                                                                                                       |
        | `data`                      | str     | Yes      | v1          | The actual content of the file. Typically a `Value` or `Variable` reference will be used here                                                                             |
        | `actionIfFileAlreadyExists` | str     | No       | v1          | optional (default=overwrite). Allowed values: overwrite (write the data to the file anyway - overwriting any previous data), skip (leave the current file as is and skip) |
        | `fileMode`                  | str     | No       | v1          | optional (default=normal). Allowed values: normal (chmod 600) or executable (chmod 700)                                                                                   |
 
        Args:
            task: The `Task` of kind `ShellScript` version `v1` to process
            command: The command is ignored for ShellScript processing - any task of this kind will ALWAYS be processed regardless of the command.
            context: The context is ignored for ShellScript processing - any task of this kind will ALWAYS be processed regardless of the context.
            key_value_store: An instance of the `KeyValueStore`. If none is supplied, a new instance will be created.
            state_persistence: An implementation of `StatePersistence` that the task processor can use to retrieve previous copies of the `Task` manifest in order to determine the actions to be performed.

        Returns:
            An updated `KeyValueStore`.

            * `task.kind:task.task_id:command:context:FILE_PATH` - The full path to the file
            * `task.kind:task.task_id:command:context:WRITTEN` - Boolean, where a TRUE value means the file was processed.
            * `task.kind:task.task_id:command:context:EXECUTABLE` - Boolean value which will be TRUE if the file has been set as executable
            * `task.kind:task.task_id:command:context:SIZE` - The file size in BYTES
            * `task.kind:task.task_id:command:context:SHA256_CHECKSUM` - The calculated file checksum (SHA256)

        Raises:
            Exception: As determined by the processing logic.
        """
        self.spec = copy.deepcopy(task.spec)
        self.metadata = copy.deepcopy(task.metadata)
        new_key_value_store = KeyValueStore()
        new_key_value_store.store = copy.deepcopy(key_value_store.store)
        log_header = self.format_log_header(task=task, command=command, context=context)
        self.log(message='PROCESSING START - Describe', build_log_message_header=False, level='info', header=log_header)
        self.log(message='   spec: {}'.format(json.dumps(self.spec)), build_log_message_header=False, level='debug', header=log_header)
        if '{}:{}:{}:{}:RESULT'.format(task.kind,task.task_id,command,context) in key_value_store.store is True:
            self.log(message='The task have already been processed and will now be ignored. The KeyValueStore will be returned unmodified.', build_log_message_header=False, level='warning', header=log_header)
            return new_key_value_store

        

        self.spec = dict()
        self.metadata = dict()
        self.log(message='DONE', build_log_message_header=False, level='info', header=log_header)
        return new_key_value_store

