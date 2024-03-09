import copy
import re
from opus.operarius import Hook, Task, KeyValueStore, LoggerWrapper, TaskLifecycleStage


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

    # matches = re.findall('(\$\{KVS:[\w|\-|\s|:|.|;|_]+\})', 'wc -l ${KVS:prompt_output_path:RESULT} > ${KVS:prompt_output_path:RESULT}_STATS && rm -vf ${KVS:prompt_output_2_path:RESULT}')
    # ['${KVS:prompt_output_path:RESULT}', '${KVS:prompt_output_path:RESULT}', '${KVS:prompt_output_2_path:RESULT}']

    return new_key_value_store
