import copy
import traceback
from pathlib import Path
import subprocess
import tempfile
import chardet
import os
import json
from opus.operarius import LoggerWrapper, TaskProcessor, KeyValueStore, Task, StatePersistence


class ShellScript(TaskProcessor):
    """The `ShellScript` task processor executes a shell script based on the provided spec.

    By default, any `ShellScript` task will be processed, regardless of `command` and `context`. To exclude a 
    `ShellScript` task from being processed in specific cases, use the appropriate contextual identifiers, for example:

    ```python
    metadata = {
        "contextualIdentifiers": [
            {
                "type": 'ExecutionScope',
                "key": 'INCLUDE',               # Only consider processing this task if the supplied processing context
                "contexts": [                   # is one of the listed environments
                    {
                        "type": "Environment",
                        "names": [
                            "sandbox",
                            "test",
                            "prod"
                        ]
                    }
                ]
            },
            {
                "type": 'ExecutionScope',
                "key": 'EXCLUDE',               # Specifically exclude this task from being processed during "delete"
                "contexts": [                   # commands
                    {
                        "type": "Command",
                        "names": [
                            "delete"
                        ]
                    }
                ]
            }
        ]
    }
    task = Task(kind='ShellScript', version='v1', spec=..., metadata=metadata, logger=...)
    ```

    Attributes:
        logger: An implementation of the `LoggerWrapper` class
        kind: The kind. Any `Task` with the same kind (and matching version) may be processed with this task processor.
        versions: A list of supported versions that this task processor can process
        supported_commands: A list of supported commands that this task processor can process on matching tasks.
    """

    def __init__(self, kind: str='ShellScript', kind_versions: list=['v1',], supported_commands: list = list(), logger: LoggerWrapper = LoggerWrapper()):
        self.spec = dict()
        super().__init__(kind, kind_versions, supported_commands, logger)

    def _id_source(self, log_header: str='')->str:
        source = 'inline'
        if 'source' in self.spec:
            if 'type' in self.spec['source']:
                if self.spec['source']['type'] in ('inLine', 'filePath',):
                    source = self.spec['source']['type']
        return source

    def _load_source_from_spec(self, log_header: str='')->str:
        source = 'exit 0'
        if 'source' in self.spec:
            if 'value' in self.spec['source']:
                source = self.spec['source']['value']
        return source

    def _load_source_from_file(self, log_header: str='')->str:
        source = 'exit 0'
        if 'source' in self.spec:
            if 'value' in self.spec['source']:
                try:
                    self.log(message='   Loading script source from file "{}"'.format(self.spec['source']['value']), level='info', build_log_message_header=False , header=log_header)
                    with open(self.spec['source']['value'], 'r') as f:
                        source = f.read()
                except:
                    self.log(message='   EXCEPTION: {}'.format(traceback.format_exc()), level='error', build_log_message_header=False , header=log_header)
        return source

    def _get_work_dir(self, log_header: str='')->str:
        work_dir = tempfile.gettempdir()
        if 'workDir' in self.spec:
            if 'path' in self.spec['workDir']:
                work_dir = self.spec['workDir']['path']
        self.log(message='   Work directory set to "{}"'.format(work_dir), level='info', build_log_message_header=False , header=log_header)
        return work_dir

    def _del_file(self, file: str, log_header: str=''):
        try:
            os.unlink(file)
        except:
            pass

    def _create_work_file(self, source:str, log_header: str='')->str:
        work_file = '{}{}{}'.format(
            self._get_work_dir(),
            os.sep,
            self.metadata['name']
        )
        self.log(message='   Writing source code to file "{}"'.format(work_file), level='info', build_log_message_header=False , header=log_header)
        self._del_file(file=work_file)
        try:
            with open(work_file, 'w') as f:
                f.write(source)
            self.log(message='      DONE', level='info', build_log_message_header=False , header=log_header)
        except:
            self.log(message='   EXCEPTION in _create_work_file(): {}'.format(traceback.format_exc()), level='error', build_log_message_header=False , header=log_header)
        return work_file

    def __detect_encoding(self, input_str: str)->str:
        encoding = None
        try:
            encoding = chardet.detect(input_str)['encoding']
        except:
            pass
        return encoding

    def process_task(self, task: Task, command: str, context: str='default', key_value_store: KeyValueStore=KeyValueStore(), state_persistence: StatePersistence=StatePersistence())->KeyValueStore:
        """Regardless of command and context, the specified shell script will be run, unless specifically excluded.

        # Spec fields

        Root levels spec fields

        | Field                        | Type     | Required | In Versions | Description                                                                                                                                                                                                                                     |
        | ---------------------------- | :------: | :------: | :---------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
        | `shellInterpreter`           |  str     |    No    |     v1      | The shell interpreter to select in the shabang line. Supported values: `sh`, `zsh`, `perl`, `python` and `bash`                                                                                                                                 |
        | `source`                     |  dict    |    Yes   |     v1      | Defines the script source                                                                                                                                                                                                                       |
        | `workDir`                    |  dict    |    No    |     v1      | Defines work directory attributes..                                                                                                                                                                                                             |
        | `convertOutputToText`        |  bool    |    No    |     v1      | Normally the STDOUT and STDERR will be binary encoded. Setting this value to true will convert those values to a normal string. Default=False                                                                                                   |
        | `stripNewline`               |  bool    |    No    |     v1      | Output may include newline or other line break characters. Setting this value to true will remove newline characters. Default=False                                                                                                             |
        | `convertRepeatingSpaces`     |  bool    |    No    |     v1      | Output may contain more than one repeating space or tab characters. Setting this value to true will replace these with a single space. Default=False                                                                                            |
        | `stripLeadingTrailingSpaces` |  bool    |    No    |     v1      | Output may contain more than one repeating space or tab characters. Setting this value to true will replace these with a single space. Default=False                                                                                            |
        | `raiseExceptionOnError`      |  bool    |    No    |     v1      | Default value is `False`. If set to `True`, and shell processing exit code other that `0` will force an exception to be raised.                                                                                                                 |

        ## Fields of `source`

        | Field                        | Type     | Required | In Versions | Description                                                                                                                                                                                                                                     |
        | ---------------------------- | :------: | :------: | :---------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
        | `type`                       |  str     |    No    |     v1      | Select the source type, which can be either `filePath` that points to an existing script file on the local file system, or `inLine` with the script source defined in the `spec.source.value` field                                             |
        | `value`                      |  str     |    No    |     v1      | If `spec.source.type` has a value of `inLine` then the value here will be assumed to be the script content of that type. if `spec.source.type` has a value of `filePath` then this value must point to an existing file on the local filesystem |

        ## Fields for `workDir`

        | Field                        | Type     | Required | In Versions | Description                                                                                                                                                                                                                                     |
        | ---------------------------- | :------: | :------: | :---------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
        | `path`                       |  str     |    No    |     v1      | An optional path to a working directory. The `ShellScript` will create temporary files (if needed) in this directory and execute them from here.                                                                                                |        

        Args:
            task: The `Task` of kind `ShellScript` version `v1` to process
            command: The command is ignored for ShellScript processing - any task of this kind will ALWAYS be processed regardless of the command.
            context: The context is ignored for ShellScript processing - any task of this kind will ALWAYS be processed regardless of the context.
            key_value_store: An instance of the `KeyValueStore`. If none is supplied, a new instance will be created.
            state_persistence: An implementation of `StatePersistence` that the task processor can use to retrieve previous copies of the `Task` manifest in order to determine the actions to be performed.

        Returns:
            An updated `KeyValueStore`.

            * Output from STDOUT will be saved under the key: `task.kind:task.task_id:command:context:processing:result:STDOUT`
            * Output from STDERR will be saved under the key: `task.kind:task.task_id:command:context:processing:result:STDERR`
            * Script exit code will be saved under the key: `task.kind:task.task_id:command:context:processing:result:EXIT_CODE`

        Raises:
            Exception: As determined by the processing logic.
        """
        result_stdout = ''
        result_stderr = ''
        result_exit_code = 0
        new_key_value_store = KeyValueStore()
        new_key_value_store.store = copy.deepcopy(key_value_store.store)
        log_header = self.format_log_header(task=task, command=command, context=context)
        if '{}:{}:{}:processing:result:EXIT_CODE' in key_value_store.store is True:
            self.log(message='The task have already been processed and will now be ignored. The KeyValueStore will be returned unmodified.', build_log_message_header=False, level='warning', header=log_header)
            return new_key_value_store
        
        task_processing_exception_raised = False
        task_processing_exception_formatted_stacktrace = ''
        try:
            self.spec = copy.deepcopy(task.spec)
            self.log(message='process_task() CALLED', build_log_message_header=False, level='info', header=log_header)
            self.log(message='spec={}'.format(json.dumps(self.spec)), build_log_message_header=False, level='debug', header=log_header)

            ###
            ### PREP SOURCE FILE
            ###
            script_source = 'exit 0'
            if self._id_source() == 'inline':
                shabang = '#!/bin/sh'
                if 'shellInterpreter' in self.spec:
                    shabang = self.spec['shellInterpreter']
                    script_source = '#!/usr/bin/env {}\n\n{}'.format(
                        shabang,
                        self._load_source_from_spec()
                    )
                else:
                    script_source = '{}\n\n{}'.format(
                        shabang,
                        self._load_source_from_spec()
                    )
            else:
                script_source = self._load_source_from_file()
            self.log(message='script_source:\n--------------------\n{}\n--------------------'.format(script_source), build_log_message_header=False, level='debug', header=log_header)
            work_file = self._create_work_file(source=script_source)

            ###
            ### EXECUTE
            ###
            result = None
            os.chmod(work_file, 0o700)
            result = subprocess.run('{}'.format(work_file), check=True, capture_output=True)   # Returns CompletedProcess

            ###
            ### STORE VALUES
            ###
            if result is not None:
                result_stdout = result.stdout
                result_exit_code = result.returncode
                self.log(message='   Storing Variables', build_log_message_header=False, level='info', header=log_header)                
                value_stdout_encoding = self.__detect_encoding(input_str=result.stdout)
                value_stderr_encoding = self.__detect_encoding(input_str=result.stdout)
                result_stderr = result.stderr

                if 'convertOutputToText' in self.spec:
                    if self.spec['convertOutputToText'] is True:
                        if value_stdout_encoding is not None:
                            result_stdout = result_stdout.decode(value_stdout_encoding)
                        if value_stderr_encoding is not None:
                            result_stderr = result_stderr.decode(value_stderr_encoding)

                if 'stripNewline' in self.spec:
                    if self.spec['stripNewline'] is True:
                        try:
                            if result_stdout is not None:
                                result_stdout = result_stdout.replace('\n', '')
                                result_stdout = result_stdout.replace('\r', '')
                            if result_stderr is not None:
                                result_stderr = result_stderr.replace('\n', '')
                                result_stderr = result_stderr.replace('\r', '')
                        except:
                            traceback.print_exc()
                            self.log(message='Could not remove newline characters after "StripNewline" setting was set to True', build_log_message_header=False, level='warning', header=log_header)

                if 'convertRepeatingSpaces' in self.spec:
                    if self.spec['convertRepeatingSpaces'] is True:
                        try:
                            if result_stdout is not None:
                                result_stdout = ' '.join(result_stdout.split())
                            if result_stderr is not None:
                                result_stderr = ' '.join(result_stderr.split())
                        except:
                            traceback.print_exc()
                            self.log(message='Could not remove repeating whitespace characters after "ConvertRepeatingSpaces" setting was set to True', build_log_message_header=False, level='warning', header=log_header)

                if 'stripLeadingTrailingSpaces' in self.spec:
                    if self.spec['stripLeadingTrailingSpaces'] is True:
                        try:
                            if result_stdout is not None:
                                result_stdout = result_stdout.strip()
                            if result_stderr is not None:
                                result_stderr = result_stderr.strip()
                        except:
                            traceback.print_exc()
                            self.log(message='Could not remove repeating whitespace characters after "ConvertRepeatingSpaces" setting was set to True', build_log_message_header=False, level='warning', header=log_header)

                self.log(message='      Storing Exit Code', build_log_message_header=False, level='info', header=log_header)
                new_key_value_store.save(key='{}:{}:{}:{}:processing:result:EXIT_CODE'.format(task.kind, task.task_id, command, context), value=result_exit_code)

                self.log(message='      Storing STDERR', build_log_message_header=False, level='info', header=log_header)
                new_key_value_store.save(key='{}:{}:{}:{}:processing:result:STDERR'.format(task.kind, task.task_id, command, context), value=result_stderr)

                self.log(message='      Storing STDOUT', build_log_message_header=False, level='info', header=log_header)
                new_key_value_store.save(key='{}:{}:{}:{}:processing:result:STDOUT'.format(task.kind, task.task_id, command, context), value=result_stdout)

                self.log(message='      Storing ALL DONE', build_log_message_header=False, level='info', header=log_header)


        except:
            task_processing_exception_formatted_stacktrace = traceback.format_exc()
            self.log(message='EXCEPTION: {}'.format(task_processing_exception_formatted_stacktrace), build_log_message_header=False, level='error', header=log_header)
            task_processing_exception_raised = True

        if task_processing_exception_raised is True or result_exit_code != 0:
            if 'raiseExceptionOnError' in task.spec:
                if isinstance(task.spec['raiseExceptionOnError'], bool):
                    if task.spec['raiseExceptionOnError'] is True:
                        raise Exception('{} - Task Processing failed Stacktrace was logged.'.format(log_header))
            if len(task_processing_exception_formatted_stacktrace) > 0:
                if len(result_stderr) != 0:
                    result_stderr = '{}\n\n'.format(result_stderr)
                result_stderr = '{}Processing Exception Stacktrace:\n-------------------------------\n{}\n-------------------------------'.format(
                    result_stderr,
                    task_processing_exception_formatted_stacktrace
                )

        self.spec = dict()
        new_key_value_store.save(key='{}:{}:{}:processing:result:STDOUT'.format(task.task_id, command, context), value=result_stdout)
        new_key_value_store.save(key='{}:{}:{}:processing:result:STDERR'.format(task.task_id, command, context), value=result_stderr)
        new_key_value_store.save(key='{}:{}:{}:processing:result:EXIT_CODE'.format(task.task_id, command, context), value=result_exit_code)
        return new_key_value_store

