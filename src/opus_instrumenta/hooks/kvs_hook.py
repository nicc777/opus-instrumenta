import copy
import re
from opus.operarius import Hook, Task, KeyValueStore, LoggerWrapper, TaskLifecycleStage


def is_iterable(data: object, exclude_dict: bool=True, exclude_string: bool=True)->bool:
    if data is None:
        return False
    if exclude_dict is True and isinstance(data, dict):
        return False
    if exclude_string is True and isinstance(data, str):
        return False
    try:
        iter(data)
    except TypeError as te:
        return False
    return True


def lookup_value(raw_key: str, command:str, context:str, logger:LoggerWrapper, hook_name: str, key_value_store: KeyValueStore)->object:
    # Typical key in key_value_store     : MyKind:MyId:a_command:a_context:SubKey1:SubKey2 (SubKey1 is required, but anything afterwards is optional)
    # Expected raw_key is something like : ${KVS:MyId:SubKey1:SubKey2}  
    result = ''
    logger.debug('[{}]       raw_key: {}'.format(hook_name, raw_key))
    if raw_key.startswith('${KVS:'):                # ${KVS:MyId:SubKey1:SubKey2}        
        key_parts = raw_key.split(':')              # ['${KVS', 'MyId', 'SubKey1', 'SubKey2}']
        target_task_id = key_parts[1]               # MyId
        target_index = ':'.join(key_parts[2:])      # SubKey1:SubKey2
        target_index = target_index.replace('}', '')
        lookup_key_base = '{}:{}:{}:{}'.format(     # MyId:a_command:a_context:SubKey1:SubKey2
            target_task_id,
            command,
            context,
            target_index
        )
        logger.debug('[{}]         Looking for a key that looks like "{}" in key_value_store'.format(hook_name, lookup_key_base))
        # logger.debug('[{}]           Potential keys: {}'.format(hook_name, list(key_value_store.store.keys())))
        for key in list(key_value_store.store.keys()):
            logger.debug('[{}]           Looking for key "{}" in "{}"'.format(hook_name, lookup_key_base, key))
            if lookup_key_base in key:
                logger.info('[{}]             Resolved key "{}" to swap out for reference variable "{}"'.format(hook_name, key, raw_key))
                result = copy.deepcopy(key_value_store.store[key])
    else:
        raise Exception('Oops - the raw key is not what we expected: raw_key: "{}"'.format(raw_key))
    logger.debug('[{}]         Returning final result: "{}"'.format(hook_name, result))
    return result


def analyse_data(data: object, key_value_store:KeyValueStore, command:str, context:str, task_id: str, logger:LoggerWrapper, hook_name: str, task_kind: str)->dict:
    logger.info('[{}]   Analyzing data'.format(hook_name))
    logger.debug('[{}]   task "{}" - Inspecting object: {}'.format(hook_name, task_id, data))
    if data is None:
        return data
    modified_data = None
    if isinstance(data, str) is True:
        modified_data: str = copy.deepcopy(data)
        # matches = re.findall('(\$\{KVS:[\w|\-|\s|:|.|;|_]+\})', 'wc -l ${KVS:prompt_output_path:RESULT} > ${KVS:prompt_output_path:RESULT}_STATS && rm -vf ${KVS:prompt_output_2_path:RESULT}')
        # ['${KVS:prompt_output_path:RESULT}', '${KVS:prompt_output_path:RESULT}', '${KVS:prompt_output_2_path:RESULT}']
        logger.debug('[{}]     Original string: {}'.format(hook_name, data))
        matches = re.findall('(\$\{KVS:[\w|\-|\s|:|.|;|_]+\})', data)
        logger.debug('[{}]       matches: {}'.format(hook_name, matches))
        for match in matches:
            logger.debug('[{}]     Looking up value for variable placeholder "{}"'.format(hook_name, match))
            final_value = lookup_value(
                raw_key=match,
                command=command,
                context=context,
                logger=logger,
                hook_name=hook_name,
                key_value_store=copy.deepcopy(key_value_store)
            )
            modified_data = modified_data.replace(match, final_value)
    elif isinstance(data, dict) is True:
        modified_data: dict = dict()
        for key, val in data.items():
            modified_data[key] = analyse_data(data=val, key_value_store=key_value_store, command=command, context=context, task_id=task_id, logger=logger, hook_name=hook_name, task_kind=task_kind)
    elif is_iterable(data=data) is True:
        modified_data: list = list()
        for val in data:
            modified_data.append(analyse_data(data=val, key_value_store=key_value_store, command=command, context=context, task_id=task_id, logger=logger, hook_name=hook_name, task_kind=task_kind))
    else:
        modified_data = copy.deepcopy(data)

    return modified_data


def spec_variable_key_value_store_resolver(
    hook_name:str,
    task:Task,
    key_value_store:KeyValueStore,
    command:str,
    context:str,
    task_life_cycle_stage: TaskLifecycleStage,
    extra_parameters:dict,
    logger:LoggerWrapper
)->KeyValueStore:
    new_key_value_store = KeyValueStore()
    new_key_value_store.store = copy.deepcopy(key_value_store.store)

    if task_life_cycle_stage is not TaskLifecycleStage.TASK_PRE_PROCESSING_START:
        return new_key_value_store
    
    if 'SpecModifierKey' not in extra_parameters:
        return new_key_value_store
    
    spec_modifier_key = extra_parameters['SpecModifierKey']
    if spec_modifier_key is None:
        return new_key_value_store
    
    if isinstance(spec_modifier_key, str) is False:
        return new_key_value_store
    
    if 'TASK_PRE_PROCESSING_START' not in spec_modifier_key:
        return new_key_value_store

    logger.info('[{}] Called on TASK_PRE_PROCESSING_START hook event for task "{}"'.format(hook_name, task.task_id))
    logger.debug('[{}] spec_modifier_key={}'.format(hook_name, spec_modifier_key))
    logger.debug('[{}]   key_value_store keys: {}'.format(hook_name, list(key_value_store.store.keys())))

    new_key_value_store.save(
        key=spec_modifier_key,
        value=analyse_data(
            data=copy.deepcopy(task.spec),
            key_value_store=copy.deepcopy(key_value_store),
            command=command,
            context=context,
            task_id=task.task_id,
            logger=logger,
            hook_name=hook_name,
            task_kind=task.kind
        )
    )

    return new_key_value_store
