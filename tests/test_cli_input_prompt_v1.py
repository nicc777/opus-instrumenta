import sys
import os
import copy
from inspect import stack

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
print('sys.path={}'.format(sys.path))

import unittest

from opus_instrumenta.task_processors.cli_input_prompt_v1 import CliInputPrompt
from magnum_opus.operarius import LoggerWrapper, Task, Tasks, Identifier, Identifiers, IdentifierContext, IdentifierContexts, TaskProcessor, KeyValueStore

running_path = os.getcwd()
print('Current Working Path: {}'.format(running_path))


class TestLogger(LoggerWrapper):

    def __init__(self):
        super().__init__()
        self.info_lines = list()
        self.warn_lines = list()
        self.debug_lines = list()
        self.critical_lines = list()
        self.error_lines = list()
        self.all_lines_in_sequence = list()

    def info(self, message: str):
        self.info_lines.append('[LOG] INFO: {}'.format(message))
        self.all_lines_in_sequence.append(
            copy.deepcopy(self.info_lines[-1])
        )

    def warn(self, message: str):
        self.warn_lines.append('[LOG] WARNING: {}'.format(message))
        self.all_lines_in_sequence.append(
            copy.deepcopy(self.warn_lines[-1])
        )

    def warning(self, message: str):
        self.warn_lines.append('[LOG] WARNING: {}'.format(message))
        self.all_lines_in_sequence.append(
            copy.deepcopy(self.warn_lines[-1])
        )

    def debug(self, message: str):
        self.debug_lines.append('[LOG] DEBUG: {}'.format(message))
        self.all_lines_in_sequence.append(
            copy.deepcopy(self.debug_lines[-1])
        )

    def critical(self, message: str):
        self.critical_lines.append('[LOG] CRITICAL: {}'.format(message))
        self.all_lines_in_sequence.append(
            copy.deepcopy(self.critical_lines[-1])
        )

    def error(self, message: str):
        self.error_lines.append('[LOG] ERROR: {}'.format(message))
        self.all_lines_in_sequence.append(
            copy.deepcopy(self.error_lines[-1])
        )

    def reset(self):
        self.info_lines = list()
        self.warn_lines = list()
        self.debug_lines = list()
        self.critical_lines = list()
        self.error_lines = list()


def print_logger_lines(logger:LoggerWrapper):
    for line in logger.all_lines_in_sequence:
        print(line)


def dump_key_value_store(test_class_name: str, test_method_name: str, key_value_store: KeyValueStore):
    try:
        print('\n\n-------------------------------------------------------------------------------')
        print('\t\tTest Class  : {}'.format(test_class_name))
        print('\t\tTest Method : {}'.format(test_method_name))
        print('\n-------------------------------------------------------------------------------')

        # First get the max key length:
        max_key_len = 0
        for key,val in key_value_store.store.items():
            if len(key) > max_key_len:
                max_key_len = len(key)

        for key,val in key_value_store.store.items():
            final_key = '{}'.format(key)
            spaces_qty = max_key_len - len(final_key) + 1
            spaces = ' '*spaces_qty
            final_key = '{}{}: '.format(final_key, spaces)
            print('{}{}\n'.format(final_key, val))

        print('\n_______________________________________________________________________________')
    except:
        pass


class TestScenariosInLine(unittest.TestCase):    # pragma: no cover

    def setUp(self) -> None:
        print()
        print('-'*80)
        self.logger = TestLogger()
        self.tasks = Tasks(logger=self.logger)
        self.cli_input = CliInputPrompt(logger=self.logger)
        self.cli_input.map_task_processing_function_name_to_commands = dict()
        self.cli_input.link_processing_function_name_to_command(
            processing_function_name='process_task_create',
            commands=['apply', 'update',]
        )
        self.cli_input.link_processing_function_name_to_command(
            processing_function_name='process_task_destroy',
            commands=['delete',]
        )
        self.cli_input.link_processing_function_name_to_command(
            processing_function_name='process_task_describe',
            commands=['describe','info',]
        )
        self.cli_input.link_processing_function_name_to_command(
            processing_function_name='process_task_rollback',
            commands=['rollback',]
        )
        self.cli_input.link_processing_function_name_to_command(
            processing_function_name='process_task_detect_drift',
            commands=['drift', 'changes', 'diff',]
        )
        return super().setUp()

    def tearDown(self):
        print_logger_lines(logger=self.logger)
        self.logger = None
        self.tasks = None
        return super().tearDown()

    def test_echo_hello_world_default_scenario_01(self):
        scenario_commands_running_default_process = (
            'apply',
            'update',
            'delete',
            'rollback',
        )
        for scenario_command in scenario_commands_running_default_process:
            print('#'*80)
            print('###')
            print('###   COMMAND:   {}'.format(scenario_command))
            print('###')
            print('#'*80)
            task = Task(
                kind='CliInputPrompt',
                version='v1',
                metadata={
                    "identifiers": [
                        {
                            "type": "ManifestName",
                            "key": "test1"
                        },
                        {
                            "type": "Label",
                            "key": "is_unittest",
                            "value": "TRUE"
                        }
                    ]
                },
                spec={
                    'promptText': 'This is a test that will return "it worked!" after 2 seconds timeout',
                    'defaultValue': 'it worked!',
                    'promptCharacter': '$$',
                    'waitTimeoutSeconds': 1,
                },
                logger=self.logger
            )
            self.tasks = Tasks(logger=self.logger)
            self.tasks.register_task_processor(processor=self.cli_input)
            self.tasks.add_task(task=task)
            self.tasks.process_context(command=scenario_command, context='unittest')
            self.tasks.state_persistence.persist_all_state()
            dump_key_value_store(test_class_name=self.__class__.__name__, test_method_name=stack()[0][3], key_value_store=self.tasks.key_value_store)
            self.assertIsNotNone(self.tasks.key_value_store)
            self.assertIsNotNone(self.tasks.key_value_store.store)
            self.assertIsInstance(self.tasks.key_value_store, KeyValueStore)
            self.assertIsInstance(self.tasks.key_value_store.store, dict)
            self.assertTrue('PROCESSING_TASK:test1:{}:unittest'.format(scenario_command) in self.tasks.key_value_store.store)
            self.assertTrue('CliInputPrompt:test1:{}:unittest:RESULT'.format(scenario_command) in self.tasks.key_value_store.store)
            self.assertEqual(self.tasks.key_value_store.store['CliInputPrompt:test1:{}:unittest:RESULT'.format(scenario_command)], 'it worked!')
            self.tasks = None
            self.tasks = Tasks(logger=self.logger)
            print_logger_lines(logger=self.logger)
            self.logger.info_lines = list()
            self.logger.warn_lines = list()
            self.logger.debug_lines = list()
            self.logger.critical_lines = list()
            self.logger.error_lines = list()
            self.logger.all_lines_in_sequence = list()

    def test_echo_hello_world_describe_scenario_01(self):
        scenario_command = 'describe'
        print('#'*80)
        print('###')
        print('###   COMMAND:   {}'.format(scenario_command))
        print('###')
        print('#'*80)
        task = Task(
            kind='CliInputPrompt',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "test1"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ]
            },
            spec={
                'promptText': 'This is a test that will return "it worked!" after 2 seconds timeout',
                'defaultValue': 'it worked!',
                'promptCharacter': '$$',
                'waitTimeoutSeconds': 1,
            },
            logger=self.logger
        )
        self.tasks.register_task_processor(processor=self.cli_input)
        self.tasks.add_task(task=task)
        self.tasks.process_context(command=scenario_command, context='unittest')
        self.tasks.state_persistence.persist_all_state()
        dump_key_value_store(test_class_name=self.__class__.__name__, test_method_name=stack()[0][3], key_value_store=self.tasks.key_value_store)

        self.assertIsNotNone(self.tasks.key_value_store)
        self.assertIsNotNone(self.tasks.key_value_store.store)
        self.assertIsInstance(self.tasks.key_value_store, KeyValueStore)
        self.assertIsInstance(self.tasks.key_value_store.store, dict)
        self.assertTrue('PROCESSING_TASK:test1:{}:unittest'.format(scenario_command) in self.tasks.key_value_store.store)
        self.assertTrue('CliInputPrompt:test1:{}:unittest:RESULT'.format(scenario_command) in self.tasks.key_value_store.store)
        self.assertEqual(self.tasks.key_value_store.store['CliInputPrompt:test1:{}:unittest:RESULT'.format(scenario_command)], '')
        self.assertTrue('CliInputPrompt:test1:{}:unittest:RESOURCE_STATE'.format(scenario_command) in self.tasks.key_value_store.store)
        self.assertIsInstance(self.tasks.key_value_store.store['CliInputPrompt:test1:{}:unittest:RESOURCE_STATE'.format(scenario_command)], dict)
        state_result = copy.deepcopy(self.tasks.key_value_store.store['CliInputPrompt:test1:{}:unittest:RESOURCE_STATE'.format(scenario_command)])
        expected_state_result_attributes = [
            {
                'KeyName': 'Label',
                'KeyMustBePresent': True,
                'ValueType': str,
                'ValueCanBeNone': False,
                'ExpectedValue': 'test1',
            },
            {
                'KeyName': 'IsCreated',
                'KeyMustBePresent': True,
                'ValueType': str,
                'ValueCanBeNone': False,
                'ExpectedValue': 'No',
            },
            {
                'KeyName': 'CreatedTimestamp',
                'KeyMustBePresent': True,
                'ValueType': str,
                'ValueCanBeNone': False,
                'ExpectedValue': '-',
            },
            {
                'KeyName': 'SpecDrifted',
                'KeyMustBePresent': True,
                'ValueType': str,
                'ValueCanBeNone': False,
                'ExpectedValue': 'N/A',
            },
            {
                'KeyName': 'ResourceDrifted',
                'KeyMustBePresent': True,
                'ValueType': str,
                'ValueCanBeNone': False,
                'ExpectedValue': 'N/A',
            }
        ]
        for validation_data in expected_state_result_attributes:
            state_result_key = validation_data['KeyName']
            if validation_data['KeyMustBePresent'] is True:
                self.assertTrue(state_result_key in state_result)
            if state_result_key in state_result is True:
                self.assertIsInstance(state_result[state_result_key], validation_data['ValueType'])
            if validation_data['ValueCanBeNone'] is False:
                self.assertIsNotNone(state_result[state_result_key])
            self.assertEqual(state_result[state_result_key], validation_data['ExpectedValue'])

    def test_echo_hello_world_drift_scenario_01(self):
        scenario_command = 'drift'
        print('#'*80)
        print('###')
        print('###   COMMAND:   {}'.format(scenario_command))
        print('###')
        print('#'*80)
        task = Task(
            kind='CliInputPrompt',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "test1"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ]
            },
            spec={
                'promptText': 'This is a test that will return "it worked!" after 2 seconds timeout',
                'defaultValue': 'it worked!',
                'promptCharacter': '$$',
                'waitTimeoutSeconds': 1,
            },
            logger=self.logger
        )
        self.tasks.register_task_processor(processor=self.cli_input)
        self.tasks.add_task(task=task)
        self.tasks.process_context(command=scenario_command, context='unittest')
        self.tasks.state_persistence.persist_all_state()
        dump_key_value_store(test_class_name=self.__class__.__name__, test_method_name=stack()[0][3], key_value_store=self.tasks.key_value_store)

        self.assertIsNotNone(self.tasks.key_value_store)
        self.assertIsNotNone(self.tasks.key_value_store.store)
        self.assertIsInstance(self.tasks.key_value_store, KeyValueStore)
        self.assertIsInstance(self.tasks.key_value_store.store, dict)
        self.assertTrue('PROCESSING_TASK:test1:{}:unittest'.format(scenario_command) in self.tasks.key_value_store.store)
        self.assertTrue('CliInputPrompt:test1:{}:unittest:RESULT'.format(scenario_command) in self.tasks.key_value_store.store)
        self.assertEqual(self.tasks.key_value_store.store['CliInputPrompt:test1:{}:unittest:RESULT'.format(scenario_command)], 'it worked!')

        self.assertTrue('CliInputPrompt:test1:{}:unittest:DRIFT_RAW_DATA'.format(scenario_command) in self.tasks.key_value_store.store)
        self.assertIsInstance(self.tasks.key_value_store.store['CliInputPrompt:test1:{}:unittest:DRIFT_RAW_DATA'.format(scenario_command)], dict)
        
        self.assertTrue('CliInputPrompt:test1:{}:unittest:DRIFT_HUMAN_READABLE'.format(scenario_command) in self.tasks.key_value_store.store)
        self.assertIsInstance(self.tasks.key_value_store.store['CliInputPrompt:test1:{}:unittest:DRIFT_HUMAN_READABLE'.format(scenario_command)], dict)
        
        state_result = copy.deepcopy(self.tasks.key_value_store.store['CliInputPrompt:test1:{}:unittest:DRIFT_RAW_DATA'.format(scenario_command)])
        expected_state_result_attributes = [
            {
                'KeyName': 'Label',
                'KeyMustBePresent': True,
                'ValueType': str,
                'ValueCanBeNone': False,
                'ExpectedValue': 'test1',
            },
            {
                'KeyName': 'IsCreated',
                'KeyMustBePresent': True,
                'ValueType': bool,
                'ValueCanBeNone': False,
                'ExpectedValue': False,
            },
            {
                'KeyName': 'CreatedTimestamp',
                'KeyMustBePresent': True,
                'ValueType': str,
                'ValueCanBeNone': True,
                'ExpectedValue': None,
            },
            {
                'KeyName': 'SpecDrifted',
                'KeyMustBePresent': True,
                'ValueType': bool,
                'ValueCanBeNone': True,
                'ExpectedValue': None,
            },
            {
                'KeyName': 'ResourceDrifted',
                'KeyMustBePresent': True,
                'ValueType': bool,
                'ValueCanBeNone': True,
                'ExpectedValue': None,
            },
            {
                'KeyName': 'AppliedSpecChecksum',
                'KeyMustBePresent': True,
                'ValueType': str,
                'ValueCanBeNone': True,
                'ExpectedValue': None,
            },
            {
                'KeyName': 'CurrentResolvedSpecChecksum',
                'KeyMustBePresent': True,
                'ValueType': str,
                'ValueCanBeNone': False,
                'ExpectedValue': 'bddad0618bbb591ce36174ec6a8f825d5fe8bd04c15c9f8e88a70ab78ab70e82',
            },
            {
                'KeyName': 'AppliedResourcesChecksum',
                'KeyMustBePresent': True,
                'ValueType': str,
                'ValueCanBeNone': True,
                'ExpectedValue': None,
            },
            {
                'KeyName': 'CurrentResourceChecksum',
                'KeyMustBePresent': True,
                'ValueType': str,
                'ValueCanBeNone': True,
                'ExpectedValue': None,
            },
            {
                'KeyName': 'AppliedSpec',
                'KeyMustBePresent': True,
                'ValueType': dict,
                'ValueCanBeNone': False,
                'ExpectedValue': {},
            },
        ]
        for validation_data in expected_state_result_attributes:
            state_result_key = validation_data['KeyName']
            if validation_data['KeyMustBePresent'] is True:
                self.assertTrue(state_result_key in state_result)
            if state_result_key in state_result is True:
                self.assertIsInstance(state_result[state_result_key], validation_data['ValueType'])
            if validation_data['ValueCanBeNone'] is False:
                self.assertIsNotNone(state_result[state_result_key])
            self.assertEqual(state_result[state_result_key], validation_data['ExpectedValue'])


if __name__ == '__main__':
    unittest.main()
