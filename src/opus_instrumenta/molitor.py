# Hooks
from opus_instrumenta.hooks.kvs_hook import spec_variable_key_value_store_resolver

# Task Processors
from opus_instrumenta.task_processors.cli_input_prompt_v1 import CliInputPrompt
from opus_instrumenta.task_processors.shell_script_v1 import ShellScript
from opus_instrumenta.task_processors.web_download_file import WebDownloadFile

# General imports
from opus.operarius import Hook, Hooks, TaskProcessor, Tasks, LoggerWrapper, KeyValueStore, StatePersistence


STANDARD_HOOKS = [
    spec_variable_key_value_store_resolver
]


ALL_TASK_PROCESSORS = [
    CliInputPrompt(),
    ShellScript(),
    WebDownloadFile(),
]


def build_hooks(selected_hooks: list=STANDARD_HOOKS)->Hooks:
    hooks = Hooks()
    hook: Hook
    for hook in selected_hooks:
        hooks.register_hook(hook=hook)
    return hooks


def build_task_processors(selected_task_processors: list=ALL_TASK_PROCESSORS)->list:
    task_processors = list()
    task_processor: TaskProcessor
    for task_processor in selected_task_processors:
        task_processors.append(task_processor)
    return task_processors


def build_tasks(
    logger: LoggerWrapper=LoggerWrapper(),
    key_value_store: KeyValueStore=KeyValueStore(),
    state_persistence: StatePersistence=StatePersistence(),
    selected_hooks: list=STANDARD_HOOKS,
    selected_task_processors: list=ALL_TASK_PROCESSORS
)->Tasks:
    tasks = Tasks(
        logger=logger,
        key_value_store=key_value_store,
        hooks=build_hooks(selected_hooks=selected_hooks),
        state_persistence=state_persistence
    )
    for task_processor in build_task_processors(selected_task_processors=selected_task_processors):
        tasks.register_task_processor(processor=task_processor)
    return tasks

