import sys
import os
import copy
from inspect import stack
import random
import string
from  pytest_httpserver import HTTPServer
import traceback

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
print('sys.path={}'.format(sys.path))

import unittest

from opus_instrumenta.task_processors.web_download_file import WebDownloadFile
from opus_instrumenta.task_processors.cli_input_prompt_v1 import CliInputPrompt
from opus_instrumenta.task_processors.shell_script_v1 import ShellScript
from opus_instrumenta.molitor import build_tasks
from opus.operarius import LoggerWrapper, Task, Tasks, Identifier, Identifiers, IdentifierContext, IdentifierContexts, TaskProcessor, KeyValueStore, build_command_identifier

running_path = os.getcwd()
print('Current Working Path: {}'.format(running_path))


def validate_order(must_be_before_input_task_name: str, input_task_name: str, list_of_tasks: list)->bool:
    must_be_before_input_task_name_pos = list_of_tasks.index(must_be_before_input_task_name)
    input_task_name_pos = list_of_tasks.index(input_task_name)
    return must_be_before_input_task_name_pos < input_task_name_pos


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


class TestScenariosBasicGet(unittest.TestCase):    # pragma: no cover

    def setUp(self) -> None:
        print()
        print('-'*80)
        self.logger = TestLogger()
        return super().setUp()

    def tearDown(self):
        print_logger_lines(logger=self.logger)
        self.logger = None
        return super().tearDown()

    def test_calculated_task_processing_order_01(self):
        task_prompt_for_source_url = Task(
            kind='CliInputPrompt',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "prompt_url"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ]
            },
            spec={
                'promptText': 'Get a web URL for a file to download or use a default value after the timeout.',
                'defaultValue': 'https://raw.githubusercontent.com/nicc777/py-animus-extensions/main/implementations/web-download-file-v1.py',
                'promptCharacter': 'URL:',
                'waitTimeoutSeconds': 5,
            },
            logger=self.logger
        )
        task_prompt_for_output_file = Task(
            kind='CliInputPrompt',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "prompt_output_path"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ]
            },
            spec={
                'promptText': 'Supply a destination file where you want to save this file.',
                'defaultValue': '/tmp/output',
                'promptCharacter': 'PATH:',
                'waitTimeoutSeconds': 5,
            },
            logger=self.logger
        )
        task_download = Task(
            kind='WebDownloadFile',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "download"
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
                            { "key": "prompt_url" },
                            { "key": "prompt_output_path" },
                        ]
                    }
                ]
            },
            spec={
                'sourceUrl': '${KVS:prompt_url:RESULT}',
                'targetOutputFile': '${KVS:prompt_output_path:RESULT}',
            },
            logger=self.logger
        )
        task_file_test_and_cleanup = Task(
            kind='ShellScript',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "stats_and_cleanup"
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
                            { "key": "download" },
                        ]
                    }
                ]
            },
            spec={
                'source': {
                    'type': 'inline',
                    'value': 'wc -l ${KVS:prompt_output_path:RESULT} > ${KVS:prompt_output_path:RESULT}_STATS && rm -vf ${KVS:prompt_output_path:RESULT}'
                }
            },
            logger=self.logger
        )
        tasks = Tasks(logger=self.logger)

        cli_input_processor = CliInputPrompt(logger=self.logger)
        web_download_processor = WebDownloadFile(logger=self.logger)
        shell_script_processor = ShellScript(logger=self.logger)

        tasks.register_task_processor(processor=cli_input_processor)
        tasks.register_task_processor(processor=web_download_processor)
        tasks.register_task_processor(processor=shell_script_processor)

        tasks.add_task(task=task_prompt_for_source_url)
        tasks.add_task(task=task_file_test_and_cleanup)
        tasks.add_task(task=task_download)
        tasks.add_task(task=task_prompt_for_output_file)

        processing_target_identifier = build_command_identifier(command='apply', context='unittest')
        calculated_task_order = tasks.calculate_current_task_order(processing_target_identifier=processing_target_identifier)
        print('***   calculated_task_order={}'.format(calculated_task_order))
        self.assertTrue(validate_order(must_be_before_input_task_name='prompt_url', input_task_name='prompt_output_path', list_of_tasks=calculated_task_order), 'FAILED TEST: Expected prompt_url to be before prompt_output_path')
        self.assertTrue(validate_order(must_be_before_input_task_name='prompt_url', input_task_name='download', list_of_tasks=calculated_task_order), 'FAILED TEST: Expected prompt_url to be before download')
        self.assertTrue(validate_order(must_be_before_input_task_name='prompt_url', input_task_name='stats_and_cleanup', list_of_tasks=calculated_task_order), 'FAILED TEST: Expected prompt_url to be before stats_and_cleanup')
        self.assertTrue(validate_order(must_be_before_input_task_name='prompt_output_path', input_task_name='download', list_of_tasks=calculated_task_order), 'FAILED TEST: Expected prompt_output_path to be before download')
        self.assertTrue(validate_order(must_be_before_input_task_name='prompt_output_path', input_task_name='stats_and_cleanup', list_of_tasks=calculated_task_order), 'FAILED TEST: Expected prompt_output_path to be before stats_and_cleanup')
        self.assertTrue(validate_order(must_be_before_input_task_name='download', input_task_name='stats_and_cleanup', list_of_tasks=calculated_task_order), 'FAILED TEST: Expected download to be before stats_and_cleanup')

    def test_processing_using_hooks_for_variable_substitution_01(self):
        task_prompt_for_source_url = Task(
            kind='CliInputPrompt',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "prompt_url"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ]
            },
            spec={
                'promptText': 'Get a web URL for a file to download or use a default value after the timeout.',
                'defaultValue': 'https://raw.githubusercontent.com/nicc777/py-animus-extensions/main/implementations/web-download-file-v1.py',
                'promptCharacter': 'URL:',
                'waitTimeoutSeconds': 5,
            },
            logger=self.logger
        )
        task_prompt_for_output_file = Task(
            kind='CliInputPrompt',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "prompt_output_path"
                    },
                    {
                        "type": "Label",
                        "key": "is_unittest",
                        "value": "TRUE"
                    }
                ]
            },
            spec={
                'promptText': 'Supply a destination file where you want to save this file.',
                'defaultValue': '/tmp/output',
                'promptCharacter': 'PATH:',
                'waitTimeoutSeconds': 5,
            },
            logger=self.logger
        )
        task_download = Task(
            kind='WebDownloadFile',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "download"
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
                            { "key": "prompt_url" },
                            { "key": "prompt_output_path" },
                        ]
                    }
                ]
            },
            spec={
                'sourceUrl': '${KVS:prompt_url:RESULT}',
                'targetOutputFile': '${KVS:prompt_output_path:RESULT}',
            },
            logger=self.logger
        )
        task_file_test_and_cleanup = Task(
            kind='ShellScript',
            version='v1',
            metadata={
                "identifiers": [
                    {
                        "type": "ManifestName",
                        "key": "stats_and_cleanup"
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
                            { "key": "download" },
                        ]
                    }
                ]
            },
            spec={
                'source': {
                    'type': 'inline',
                    'value': 'wc -l ${KVS:prompt_output_path:RESULT} > ${KVS:prompt_output_path:RESULT}_STATS && rm -vf ${KVS:prompt_output_path:RESULT}'
                }
            },
            logger=self.logger
        )

        tasks = build_tasks(logger=self.logger)

        tasks.add_task(task=task_prompt_for_source_url)
        tasks.add_task(task=task_file_test_and_cleanup)
        tasks.add_task(task=task_download)
        tasks.add_task(task=task_prompt_for_output_file)

        processing_target_identifier = build_command_identifier(command='apply', context='unittest')
        calculated_task_order = tasks.calculate_current_task_order(processing_target_identifier=processing_target_identifier)
        print('***   calculated_task_order={}'.format(calculated_task_order))
        self.assertTrue(validate_order(must_be_before_input_task_name='prompt_url', input_task_name='prompt_output_path', list_of_tasks=calculated_task_order), 'FAILED TEST: Expected prompt_url to be before prompt_output_path')
        self.assertTrue(validate_order(must_be_before_input_task_name='prompt_url', input_task_name='download', list_of_tasks=calculated_task_order), 'FAILED TEST: Expected prompt_url to be before download')
        self.assertTrue(validate_order(must_be_before_input_task_name='prompt_url', input_task_name='stats_and_cleanup', list_of_tasks=calculated_task_order), 'FAILED TEST: Expected prompt_url to be before stats_and_cleanup')
        self.assertTrue(validate_order(must_be_before_input_task_name='prompt_output_path', input_task_name='download', list_of_tasks=calculated_task_order), 'FAILED TEST: Expected prompt_output_path to be before download')
        self.assertTrue(validate_order(must_be_before_input_task_name='prompt_output_path', input_task_name='stats_and_cleanup', list_of_tasks=calculated_task_order), 'FAILED TEST: Expected prompt_output_path to be before stats_and_cleanup')
        self.assertTrue(validate_order(must_be_before_input_task_name='download', input_task_name='stats_and_cleanup', list_of_tasks=calculated_task_order), 'FAILED TEST: Expected download to be before stats_and_cleanup')

        try:
            tasks.process_context(command='test', context='unittest')
        except:
            # traceback.format_exc()
            print_logger_lines(logger=self.logger)
            self.fail('Task processing caught an exception. Please review the logs.')

        # TODO Test if file '/tmp/output_STATS' exists. Must have content similar to: "393 /tmp/output" (INTEGER>0, SPACE, String "/tmp/output")
        # TODO Delete '/tmp/output_STATS'


if __name__ == '__main__':
    unittest.main()
