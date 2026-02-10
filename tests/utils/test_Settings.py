import pytest
from configobj import ConfigObj

from modules.utils.file.file import create_config_file


@pytest.fixture()
def data_pair() -> ConfigObj:
    config1 = ConfigObj()
    config1['test'] = {'subsection': {'test1': 'test_1', 'test2': 'test_2'}, 'testing': 'testing_1'}
    config1['global'] = {'testing_A': 'A'}
    # config.inline_comments = {'global', 'this is a test'}
    getattr(config1, 'comments')['test'] = ['this is a test for test', 'testing out the comment feature of ConfigObj']
    getattr(config1['test']['subsection'], 'inline_comments')['test1'] = 'testing test_1'
    tmp = config1['test']['subsection']
    getattr(tmp, 'inline_comments')['test2'] = 'testing test_2'
    getattr(config1['global'], 'inline_comments')['testing_A'] = 'testing testing_1'

    return config1


def test_data_pair(data_pair: ConfigObj):
    data = {'test': {'subsection': {'test1': 'test_1', 'test2': 'test_2'}, 'testing': 'testing_1'},
            'global': {'testing_A': 'A'}}

    config = create_config_file(file="../../data/tmp.ini", params=data, comments={})
    assert config == data_pair
    # config1.filename = '../../data/testing.ini'
    # config1.write()
    # pprint(f'comment\n{config1.comments}')
    # pprint(f'inline\n{config1.inline_comments}')
    # print(f'struct\n{config1}')

    # test_config = ConfigObj('../../data/testing.ini')
    # pprint(f'read in\n{test_config}')
    # pprint(test_config.comments)


def test_comments(data_pair: ConfigObj):
    data = {'test': {'subsection': {'test1': 'test_1', 'test2': 'test_2'}, 'testing': 'testing_1'},
            'global': {'testing_A': 'A'}}
    comments = {'comments': {'test': ['this is a test for test', 'testing out the comment feature of ConfigObj']},
                'inline_comments': {'test': {'subsection': {'test1': 'testing test_1'}},
                                    'global': {'testing_A': 'testing testing_1'}}}

    config: ConfigObj = create_config_file(file="../../data/tmp.ini", params=data, comments=comments)

    assert config.comments == data_pair.comments
    assert config.inline_comments == data_pair.inline_comments


def test_config_import(data_pair: ConfigObj):
    config: ConfigObj = ConfigObj("../../data/tmp.ini")
    assert config == data_pair


def test_retrieve_value(data_pair):
    data = {'test': {'subsection': {'test1': 'test_1', 'test2': 'test_2'}, 'testing': 'testing_1'},
            'global': {'testing_A': 'A'}}

    config: ConfigObj = ConfigObj("../../data/tmp.ini")
    assert data.get('test').get('subsection').get('test2') == config['test']['subsection']['test2']
