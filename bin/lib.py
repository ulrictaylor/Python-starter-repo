import datetime
import logging
import os
import tempfile

import pandas
import yaml

# Global variables
CONFS = None
BATCH_NAME = None
TEMP_DIR = None


def load_confs(confs_path='../conf/conf.yaml'):
    """
    Load configurations from file.

     - If configuration file is available, load it
     - If configuraiton file is not available attempt to load configuration template

    Configurations are never explicitly validated.
    :param confs_path: Path to a configuration file, appropriately formatted for this application
    :type confs_path: str
    :return: Python native object, containing configuration names and values
    :rtype: dict
    """
    global CONFS

    if CONFS is None:

        try:
            logging.info('Attempting to load conf from path: {}'.format(confs_path))

            # Attempt to load conf from confPath
            CONFS = yaml.load(open(confs_path))

        except IOError:
            logging.warn('Unable to open user conf file. Attempting to run with default values from conf template')

            # Attempt to load conf from template path
            template_path = confs_path + '.template'
            CONFS = yaml.load(open(template_path))

    return CONFS


def get_conf(conf_name):
    """
    Get a configuration parameter by its name
    :param conf_name: Name of a configuration parameter
    :type conf_name: str
    :return: Value for that conf (no specific type information available)
    """
    return load_confs()[conf_name]


def get_batch_name():
    """
    Get the name of the current run. This is a unique identifier for each run of this application
    :return: The name of the current run. This is a unique identifier for each run of this application
    :rtype: str
    """
    global BATCH_NAME

    if BATCH_NAME is None:
        logging.info('Batch name not yet set. Setting batch name.')
        batch_prefix = get_conf('batch_prefix')
        model_choice = get_conf('model_choice')
        datetime_str = str(datetime.datetime.utcnow().replace(microsecond=0).isoformat())+'Z'
        BATCH_NAME = '_'.join([batch_prefix, model_choice, datetime_str])
        logging.info('Batch name: {}'.format(BATCH_NAME))
    return BATCH_NAME


def get_temp_dir():
    global TEMP_DIR
    if TEMP_DIR is None:
        TEMP_DIR = tempfile.mkdtemp(prefix='python_starter')
        logging.info('Created temporary directory: {}'.format(TEMP_DIR))
        print('Created temporary directory: {}'.format(TEMP_DIR))
    return TEMP_DIR


def get_batch_output_folder():
    global BATCH_OUTPUT_FOLDER
    if BATCH_OUTPUT_FOLDER is None:
        BATCH_OUTPUT_FOLDER = os.path.join(get_conf('output_path'), get_batch_name())
        os.mkdir(BATCH_OUTPUT_FOLDER)
        logging.info('Batch output folder: {}'.format(BATCH_OUTPUT_FOLDER))
    return BATCH_OUTPUT_FOLDER


def archive_dataset_schemas(step_name, local_dict, global_dict):
    """
    Archive the schema for all available Pandas DataFrames

     - Determine which objects in namespace are Pandas DataFrames
     - Pull schema for all available Pandas DataFrames
     - Write schemas to file

    :param step_name: The name of the current operation (e.g. `extract`, `transform`, `model` or `load`
    :param local_dict: A dictionary containing mappings from variable name to objects. This is usually generated by
    calling `locals`
    :type local_dict: dict
    :param global_dict: A dictionary containing mappings from variable name to objects. This is usually generated by
    calling `globals`
    :type global_dict: dict
    :return: None
    :rtype: None
    """
    logging.info('Archiving data set schema(s) for step name: {}'.format(step_name))

    # Reference variables
    data_schema_dir = os.path.join(get_batch_output_folder(), 'schemas')
    if not os.path.exists(data_schema_dir):
        os.makedirs(data_schema_dir)
    schema_output_path = os.path.join(data_schema_dir, step_name + '.csv')
    schema_agg = list()

    env_variables = dict()
    env_variables.update(local_dict)
    env_variables.update(global_dict)

    # Filter down to Pandas DataFrames
    data_sets = filter(lambda (k, v): type(v) == pandas.DataFrame, env_variables.iteritems())
    data_sets = dict(data_sets)

    header = pandas.DataFrame(columns=['variable', 'type', 'data_set'])
    schema_agg.append(header)

    for (data_set_name, data_set) in data_sets.iteritems():
        # Extract variable names
        logging.info('Working data_set: {}'.format(data_set_name))

        local_schema_df = pandas.DataFrame(data_set.dtypes, columns=['type'])
        local_schema_df['data_set'] = data_set_name

        schema_agg.append(local_schema_df)

    # Aggregate schema list into one data frame
    agg_schema_df = pandas.concat(schema_agg)

    # Write to file
    agg_schema_df.to_csv(schema_output_path, index_label='variable')
