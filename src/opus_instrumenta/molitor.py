from pathlib import Path
import os

# Persistence
from opus_instrumenta.persistence.file_based_state_persistence import FileBasedStatePersistence

# Hooks
from opus_instrumenta.hooks.kvs_hook import spec_variable_key_value_store_resolver

# Task Processors
from opus_instrumenta.task_processors.cli_input_prompt_v1 import CliInputPrompt
from opus_instrumenta.task_processors.shell_script_v1 import ShellScript
from opus_instrumenta.task_processors.web_download_file import WebDownloadFile

# General imports
from magnum_opus.operarius import Hook, Hooks, TaskProcessor, Tasks, LoggerWrapper, KeyValueStore, StatePersistence, TaskLifecycleStage, TaskLifecycleStages


def build_task_lifecycle_stages(task_lifecycle_stages_list: list)->TaskLifecycleStages:
    task_life_cycle_stages = TaskLifecycleStages(init_default_stages=False)
    stage: TaskLifecycleStage
    for stage in task_lifecycle_stages_list:
        if isinstance(stage, TaskLifecycleStage):
            task_life_cycle_stages.register_lifecycle_stage(task_life_cycle_stage=stage)
    return task_life_cycle_stages


STANDARD_HOOKS = {
    'spec_variable_key_value_store_resolver': {
        'Function': spec_variable_key_value_store_resolver,
        'Commands': ['ALL'],
        'Contexts': ['ALL'],
        'TaskLifeCycleStages': build_task_lifecycle_stages(task_lifecycle_stages_list=[TaskLifecycleStage.TASK_PRE_PROCESSING_START,],)
    },
}


ALL_TASK_PROCESSORS = [
    CliInputPrompt(),
    ShellScript(),
    WebDownloadFile(),
]


def build_hooks(selected_hooks: dict=STANDARD_HOOKS)->Hooks:
    hooks = Hooks()
    hook: Hook
    for hook_name, hook_config in selected_hooks.items():
        hook = Hook(
            name=hook_name,
            commands=hook_config['Commands'],
            contexts=hook_config['Contexts'],
            task_life_cycle_stages=hook_config['TaskLifeCycleStages'],
            function_impl=hook_config['Function']
        )
        hooks.register_hook(hook=hook)
    return hooks


def build_file_based_state_persistence_instance(file: str=None, logger: LoggerWrapper=LoggerWrapper())->StatePersistence:
    if file is None:
        home_dir = str(Path.home())
        opus_configuration_directory = '{}{}.opus'.format(home_dir, os.sep)
        file = '{}{}persistence_data.json'.format(opus_configuration_directory, os.sep)
        if os.path.exists(opus_configuration_directory) is False:
            os.mkdir(path=opus_configuration_directory)
    return FileBasedStatePersistence(logger=logger, configuration={'StateFile': file})



def build_task_processors(
    selected_task_processors: list=ALL_TASK_PROCESSORS,
    logger: LoggerWrapper=LoggerWrapper(),
    state_persistence: StatePersistence=StatePersistence()
)->list:
    task_processors = list()
    task_processor: TaskProcessor
    for task_processor in selected_task_processors:
        task_processor.logger = logger
        task_processor.state_persistence = state_persistence
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
    task_processor: TaskProcessor
    for task_processor in build_task_processors(
        selected_task_processors=selected_task_processors,
        logger=logger,
        state_persistence=state_persistence
    ):
        task_processor.link_processing_function_name_to_command(
            processing_function_name='process_task_create',
            commands=['apply', 'update',]
        )
        task_processor.link_processing_function_name_to_command(
            processing_function_name='process_task_destroy',
            commands=['delete',]
        )
        task_processor.link_processing_function_name_to_command(
            processing_function_name='process_task_describe',
            commands=['describe','info',]
        )
        task_processor.link_processing_function_name_to_command(
            processing_function_name='process_task_rollback',
            commands=['rollback',]
        )
        task_processor.link_processing_function_name_to_command(
            processing_function_name='process_task_detect_drift',
            commands=['drift', 'changes', 'diff',]
        )
        tasks.register_task_processor(processor=task_processor)
    return tasks

