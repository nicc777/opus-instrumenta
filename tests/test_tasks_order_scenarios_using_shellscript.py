import sys
import os
import copy
from inspect import stack
from itertools import permutations

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
print('sys.path={}'.format(sys.path))

import unittest

from opus_instrumenta.task_processors.shell_script_v1 import ShellScript
from magnum_opus.operarius import LoggerWrapper, Task, Tasks, Identifier, Identifiers, IdentifierContext, IdentifierContexts, TaskProcessor, KeyValueStore, build_command_identifier

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


def validate_order(must_be_before_input_task_name: str, input_task_name: str, list_of_tasks: list)->bool:
    must_be_before_input_task_name_pos = list_of_tasks.index(must_be_before_input_task_name)
    input_task_name_pos = list_of_tasks.index(input_task_name)
    return must_be_before_input_task_name_pos < input_task_name_pos


class TestScenariosInLine(unittest.TestCase):    # pragma: no cover

    def setUp(self) -> None:
        print()
        print('-'*80)
        self.logger = TestLogger()
        return super().setUp()

    def tearDown(self):
        print_logger_lines(logger=self.logger)
        self.logger = None
        return super().tearDown()

    def test_order_expected_to_work_01(self):
        shell_script = ShellScript(logger=self.logger)
        t_1 = Task(
            kind='ShellScript',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "t_1"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ],
                "dependencies": [
                    {
                        "identifierType": "ManifestName",
                        "identifiers": [
                            { "key": "t_2" },
                            { "key": "t_3" },
                        ]
                    }
                ]
            },
            spec={
                'source': {
                    'type': 'inline',
                    'value': 'echo "r_1"'
                },
                'convertOutputToText': True,
                'stripNewline': True,
                'convertRepeatingSpaces': True,
                'stripLeadingTrailingSpaces': True
            },
            logger=self.logger
        )
        t_2 = Task(
            kind='ShellScript',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "t_2"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ],
                "dependencies": [
                    {
                        "identifierType": "ManifestName",
                        "identifiers": [
                            { "key": "t_3" },
                        ]
                    }
                ]
            },
            spec={
                'source': {
                    'type': 'inline',
                    'value': 'echo "r_2"'
                },
                'convertOutputToText': True,
                'stripNewline': True,
                'convertRepeatingSpaces': True,
                'stripLeadingTrailingSpaces': True
            },
            logger=self.logger
        )
        t_3 = Task(
            kind='ShellScript',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "t_3"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ]
            },
            spec={
                'source': {
                    'type': 'inline',
                    'value': 'echo "r_3"'
                },
                'convertOutputToText': True,
                'stripNewline': True,
                'convertRepeatingSpaces': True,
                'stripLeadingTrailingSpaces': True
            },
            logger=self.logger
        )
        t_4 = Task(
            kind='ShellScript',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "t_4"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ],
                "dependencies": [
                    {
                        "identifierType": "ManifestName",
                        "identifiers": [
                            { "key": "t_1" },
                            { "key": "t_2" },
                        ]
                    }
                ]
            },
            spec={
                'source': {
                    'type': 'inline',
                    'value': 'echo "r_4"'
                },
                'convertOutputToText': True,
                'stripNewline': True,
                'convertRepeatingSpaces': True,
                'stripLeadingTrailingSpaces': True
            },
            logger=self.logger
        )

        tasks_to_process = [t_1,t_2,t_3,t_4]
        permutations_of_tasks = list(permutations(tasks_to_process))

        processing_target_identifier = build_command_identifier(command='test', context='test')
        set_nr = 0
        for permutation_set in permutations_of_tasks:
            set_nr += 1
            print('Set #{}'.format(set_nr))
            tasks = Tasks(logger=self.logger)
            tasks.register_task_processor(processor=shell_script)
            task: Task
            added_task_order = list()
            for task in permutation_set:
                print('   Adding task "{}"'.format(task.task_id))
                added_task_order.append(task.task_id)
                tasks.add_task(task=task)
            calculated_task_order = tasks.calculate_current_task_order(processing_target_identifier=processing_target_identifier)
            print('   calculated_task_order={}'.format(calculated_task_order))
            tasks = None
            self.assertTrue(validate_order(must_be_before_input_task_name='t_2', input_task_name='t_1', list_of_tasks=calculated_task_order), 'Set #{} - Expected t_2 to be before t_1: added_task_order={}   calculated_task_order={}'.format(set_nr, added_task_order, calculated_task_order))
            self.assertTrue(validate_order(must_be_before_input_task_name='t_3', input_task_name='t_1', list_of_tasks=calculated_task_order), 'Set #{} - Expected t_3 to be before t_1: added_task_order={}   calculated_task_order={}'.format(set_nr, added_task_order, calculated_task_order))
            self.assertTrue(validate_order(must_be_before_input_task_name='t_3', input_task_name='t_2', list_of_tasks=calculated_task_order), 'Set #{} - Expected t_3 to be before t_2: added_task_order={}   calculated_task_order={}'.format(set_nr, added_task_order, calculated_task_order))
            self.assertTrue(validate_order(must_be_before_input_task_name='t_1', input_task_name='t_4', list_of_tasks=calculated_task_order), 'Set #{} - Expected t_1 to be before t_4: added_task_order={}   calculated_task_order={}'.format(set_nr, added_task_order, calculated_task_order))
            self.assertTrue(validate_order(must_be_before_input_task_name='t_2', input_task_name='t_4', list_of_tasks=calculated_task_order), 'Set #{} - Expected t_2 to be before t_4: added_task_order={}   calculated_task_order={}'.format(set_nr, added_task_order, calculated_task_order))

    def test_dependant_tasks_processing_with_verified_results_01(self):
        shell_script = ShellScript(logger=self.logger)
        t_1 = Task(
            kind='ShellScript',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "t_1"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ],
                "dependencies": [
                    {
                        "identifierType": "ManifestName",
                        "identifiers": [
                            { "key": "t_2" },
                            { "key": "t_3" },
                        ]
                    }
                ]
            },
            spec={
                'source': {
                    'type': 'inline',
                    'value': 'echo "r_1"'
                },
                'convertOutputToText': True,
                'stripNewline': True,
                'convertRepeatingSpaces': True,
                'stripLeadingTrailingSpaces': True
            },
            logger=self.logger
        )
        t_2 = Task(
            kind='ShellScript',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "t_2"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ],
                "dependencies": [
                    {
                        "identifierType": "ManifestName",
                        "identifiers": [
                            { "key": "t_3" },
                        ]
                    }
                ]
            },
            spec={
                'source': {
                    'type': 'inline',
                    'value': 'echo "r_2"'
                },
                'convertOutputToText': True,
                'stripNewline': True,
                'convertRepeatingSpaces': True,
                'stripLeadingTrailingSpaces': True
            },
            logger=self.logger
        )
        t_3 = Task(
            kind='ShellScript',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "t_3"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ]
            },
            spec={
                'source': {
                    'type': 'inline',
                    'value': 'echo "r_3"'
                },
                'convertOutputToText': True,
                'stripNewline': True,
                'convertRepeatingSpaces': True,
                'stripLeadingTrailingSpaces': True
            },
            logger=self.logger
        )
        t_4 = Task(
            kind='ShellScript',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "t_4"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ],
                "dependencies": [
                    {
                        "identifierType": "ManifestName",
                        "identifiers": [
                            { "key": "t_1" },
                            { "key": "t_2" },
                        ]
                    }
                ]
            },
            spec={
                'source': {
                    'type': 'inline',
                    'value': 'echo "r_4"'
                },
                'convertOutputToText': True,
                'stripNewline': True,
                'convertRepeatingSpaces': True,
                'stripLeadingTrailingSpaces': True
            },
            logger=self.logger
        )

        tasks_to_process = [t_1,t_2,t_3,t_4]
        tasks = Tasks(logger=self.logger)
        tasks.register_task_processor(processor=shell_script)
        task: Task
        for task in tasks_to_process:
            print('   Adding task "{}"'.format(task.task_id))
            tasks.add_task(task=task)
        tasks.process_context(command='apply', context='unittest')
        dump_key_value_store(test_class_name=self.__class__.__name__, test_method_name=stack()[0][3], key_value_store=tasks.key_value_store)
        for task_id in ('t_1','t_2','t_3','t_4',):

            self.assertTrue('PROCESSING_TASK:{}:apply:unittest'.format(task_id) in tasks.key_value_store.store)
            self.assertIsInstance(tasks.key_value_store.store['PROCESSING_TASK:{}:apply:unittest'.format(task_id)], int)
            self.assertEqual(tasks.key_value_store.store['PROCESSING_TASK:{}:apply:unittest'.format(task_id)], 2)

            self.assertTrue('ShellScript:{}:apply:unittest:processing:result:EXIT_CODE'.format(task_id) in tasks.key_value_store.store)
            self.assertIsInstance(tasks.key_value_store.store['ShellScript:{}:apply:unittest:processing:result:EXIT_CODE'.format(task_id)], int)
            self.assertEqual(tasks.key_value_store.store['ShellScript:{}:apply:unittest:processing:result:EXIT_CODE'.format(task_id)], 0)

            self.assertTrue('ShellScript:{}:apply:unittest:processing:result:STDERR'.format(task_id) in tasks.key_value_store.store)
            self.assertIsInstance(tasks.key_value_store.store['ShellScript:{}:apply:unittest:processing:result:STDERR'.format(task_id)], str)
            self.assertEqual(tasks.key_value_store.store['ShellScript:{}:apply:unittest:processing:result:STDERR'.format(task_id)], '')

            result = task_id.replace('t', 'r')
            self.assertTrue('ShellScript:{}:apply:unittest:processing:result:STDOUT'.format(task_id) in tasks.key_value_store.store)
            self.assertIsInstance(tasks.key_value_store.store['ShellScript:{}:apply:unittest:processing:result:STDOUT'.format(task_id)], str)
            self.assertEqual(tasks.key_value_store.store['ShellScript:{}:apply:unittest:processing:result:STDOUT'.format(task_id)], result)


if __name__ == '__main__':
    unittest.main()
