import copy
import traceback
from pathlib import Path
import subprocess
import tempfile
import chardet
import os
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

            * Output from STDOUT will be saved under the key: `task.task_id:command:context:processing:result:STDOUT`
            * Output from STDERR will be saved under the key: `task.task_id:command:context:processing:result:STDERR`

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
            self.log(message='The task have already been processed and will now be ignored. The KeyValueStore will be returned unmodified.', build_log_message_header=False , level='warning', header=log_header)
            return new_key_value_store
        

        new_key_value_store.save(key='{}:{}:{}:processing:result:STDOUT'.format(task.task_id, command, context), value=result_stdout)
        new_key_value_store.save(key='{}:{}:{}:processing:result:STDERR'.format(task.task_id, command, context), value=result_stderr)
        new_key_value_store.save(key='{}:{}:{}:processing:result:EXIT_CODE'.format(task.task_id, command, context), value=result_exit_code)
        return new_key_value_store