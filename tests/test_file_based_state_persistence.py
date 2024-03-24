import sys
import os
import copy
import json
from inspect import stack

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
print('sys.path={}'.format(sys.path))

import unittest

from opus_instrumenta.persistence.file_based_state_persistence import FileBasedStatePersistence
from magnum_opus.operarius import LoggerWrapper, StatePersistence
from opus_adstator.file_io import get_file_size, read_text_file, file_exists

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


class TestScenariosInLine(unittest.TestCase):    # pragma: no cover

    def setUp(self) -> None:
        print()
        print('-'*80)
        self.logger = TestLogger()
        self.state_file = 'state_test_file.json'

    def tearDown(self) -> None:
        self.logger = None
        os.unlink(self.state_file)
        return super().tearDown()
    
    def test_basic_file_persistence_01(self):
        fp = FileBasedStatePersistence(logger=self.logger, configuration={'StateFile': self.state_file})
        self.assertTrue(file_exists(file=self.state_file))
        self.assertTrue(get_file_size(file_path=self.state_file) > 0)

        fp.save_object_state(object_identifier='testKey', data={'testValue': 123})
        fp.persist_all_state()

        data_as_json = read_text_file(path_to_file=self.state_file)
        data_as_dict = json.loads(data_as_json)
        self.assertIsNotNone(data_as_dict)
        self.assertIsInstance(data_as_dict, dict)
        self.assertTrue('testKey' in data_as_dict)
        self.assertIsNotNone(data_as_dict['testKey'])
        self.assertIsInstance(data_as_dict['testKey'], dict)
        test_key_data = data_as_dict['testKey']
        self.assertTrue('testValue' in test_key_data)
        self.assertEqual(test_key_data['testValue'], 123)
        self.assertEqual(len(data_as_dict), 1)

        fp = None

        # Re-read from the previous persisted file
        fp2 = FileBasedStatePersistence(logger=self.logger, configuration={'StateFile': self.state_file})
        self.assertTrue('testKey' in fp2.state_cache)
        test_key_data2 = fp2.state_cache['testKey']
        self.assertTrue('testValue' in test_key_data2)
        self.assertEqual(test_key_data2['testValue'], 123)


if __name__ == '__main__':
    unittest.main()
