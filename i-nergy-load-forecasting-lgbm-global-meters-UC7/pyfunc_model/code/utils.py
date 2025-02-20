
import tempfile
import pretty_errors
import os
import mlflow
import pandas as pd
import yaml
import darts
cur_dir = os.path.dirname(os.path.realpath(__file__))
import numpy as np
from tqdm import tqdm
import logging
from exceptions import MandatoryArgNotSet, NotValidConfig
import json
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
disable_warnings(InsecureRequestWarning)
import requests
from datetime import date
class ConfigParser:
    def __init__(self, config_file=f'{cur_dir}/config.yml', config_string=None):
        import yaml
        try:
            with open(config_file, "r") as ymlfile:
                self.config = yaml.safe_load(ymlfile)
                print(self.config)
                if config_string != None:
                    assert config_string in self.config['hyperparameters']
        except:
            try:
                self.config = yaml.safe_load(config_string)
            except:
                raise NotValidConfig()

    def read_hyperparameters(self, hyperparams_entrypoint=""):
            try:
                return self.config['hyperparameters'][hyperparams_entrypoint]
            except:
                return self.config

    def read_entrypoints(self):
        return self.config['hyperparameters']


def download_file_from_s3_bucket(object_name, dst_filename, dst_dir=None, bucketName='mlflow-bucket'):
    import boto3
    import tempfile
    if dst_dir is None:
        dst_dir = tempfile.mkdtemp()
    else:
        os.makedirs(dst_dir, exist_ok=True)
    os.makedirs(dst_dir, exist_ok=True)
    s3_resource = boto3.resource(
        's3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    bucket = s3_resource.Bucket(bucketName)
    local_path = os.path.join(dst_dir, dst_filename)
    bucket.download_file(object_name, local_path)
    return local_path


def load_yaml_as_dict(filepath):
    import yaml
    with open(filepath, 'r') as stream:
        try:
            parsed_yaml = yaml.safe_load(stream)
            return parsed_yaml
        except yaml.YAMLError as exc:
            print(exc)
            return

def save_dict_as_yaml(filepath, data):
    with open(filepath, 'w') as savefile:
        yaml.dump(data, savefile, default_flow_style=False)

def load_local_pkl_as_object(local_path):
    import pickle
    pkl_object = pickle.load(open(local_path, "rb"))
    return pkl_object


def download_online_file(url, dst_filename=None, dst_dir=None):
    import sys
    import tempfile
    import requests
    print("Donwloading_online_file")
    print(url)
    if dst_dir is None:
        dst_dir = tempfile.mkdtemp()
    else:
        os.makedirs(dst_dir, exist_ok=True)
    req = requests.get(url)
    if req.status_code != 200:
        raise Exception(f"\nResponse is not 200\nProblem downloading: {url}")
        sys.exit()
    url_content = req.content
    if dst_filename is None:
        dst_filename = url.split('/')[-1]
    filepath = os.path.join(dst_dir, dst_filename)
    file = open(filepath, 'wb')
    file.write(url_content)
    file.close()
    return filepath


def download_mlflow_file(url, dst_dir=None):
    S3_ENDPOINT_URL = os.environ.get('MLFLOW_S3_ENDPOINT_URL')

    if dst_dir is None:
        dst_dir = tempfile.mkdtemp()
    else:
        os.makedirs(dst_dir, exist_ok=True)
    if url.startswith('s3://mlflow-bucket/'):
        url = url.replace("s3:/", S3_ENDPOINT_URL)
        local_path = download_online_file(
            url, dst_dir=dst_dir)
    elif url.startswith('runs:/'):
        client = mlflow.tracking.MlflowClient()
        run_id = url.split('/')[1]
        mlflow_path = '/'.join(url.split('/')[3:])
        local_path = client.download_artifacts(run_id, mlflow_path, dst_dir)
    elif url.startswith('http://'):
        local_path = download_online_file(
            url, dst_dir=dst_dir)
    return local_path


def load_pkl_model_from_server(model_uri):
    print("\nLoading remote PKL model...")
    model_path = download_mlflow_file(f'{model_uri}/_model.pkl')
    print(model_path)
    best_model = load_local_pkl_as_object(model_path)
    return best_model


def load_local_pl_model(model_root_dir):

    from darts.models.forecasting.gradient_boosted_model import LightGBMModel
    from darts.models.forecasting.random_forest import RandomForest
    from darts.models import RNNModel, BlockRNNModel, NBEATSModel, TFTModel, NaiveDrift, NaiveSeasonal, TCNModel, NHiTSModel, TransformerModel
    print("\nLoading local PL model...")
    model_info_dict = load_yaml_as_dict(
        os.path.join(model_root_dir, 'model_info.yml'))

    darts_forecasting_model = model_info_dict[
        "darts_forecasting_model"]

    model = eval(darts_forecasting_model)

    # model_root_dir = model_root_dir.replace('/', os.path.sep)

    print(f"Loading model from local directory:{model_root_dir}")

    best_model = model.load_from_checkpoint(model_root_dir, best=True)

    return best_model


def load_pl_model_from_server(model_root_dir):

    import tempfile

    print("\nLoading remote PL model...")
    client = mlflow.tracking.MlflowClient()
    print(model_root_dir)
    model_run_id = model_root_dir.split("/")[5]
    mlflow_relative_model_root_dir = model_root_dir.split("/artifacts/")[1]

    local_dir = tempfile.mkdtemp()
    client.download_artifacts(
        run_id=model_run_id, path=mlflow_relative_model_root_dir, dst_path=local_dir)
    best_model = load_local_pl_model(os.path.join(
        local_dir, mlflow_relative_model_root_dir))
    return best_model


def load_model(model_root_dir, mode="remote"):

    # Get model type as tag of model's run
    import mlflow
    print(model_root_dir)

    if mode == 'remote':
        client = mlflow.tracking.MlflowClient()
        run_id = model_root_dir.split('/')[-1]
        model_run = client.get_run(run_id)
        model_type = model_run.data.tags.get('model_type')
    else:
        if "_model.pth.tar" in os.listdir(model_root_dir):
            model_type = 'pl'
        else:
            model_type = "pkl"

    # Load accordingly
    if mode == "remote" and model_type == "pl":
        model = load_pl_model_from_server(model_root_dir=model_root_dir)
    elif mode == "remote" and model_type == "pkl":
        model = load_pkl_model_from_server(model_root_dir)
    elif mode == "local" and model_type == 'pl':
        model = load_local_pl_model(model_root_dir=model_root_dir)
    else:
        print("\nLoading local PKL model...")
        # pkl loads the exact model file so:
        model_uri = os.path.join(model_root_dir, '_model.pkl')
        model = load_local_pkl_as_object(model_uri)
    return model


def load_scaler(scaler_uri=None, mode="remote"):

    import tempfile

    if scaler_uri is None:
        print("\nNo scaler loaded.")
        return None

    if mode == "remote":
        run_id = scaler_uri.split("/")[-2]
        mlflow_filepath = scaler_uri.split("/artifacts/")[1]

        client = mlflow.tracking.MlflowClient()
        local_dir = tempfile.mkdtemp()
        print("Scaler: ", scaler_uri)
        print("Run: ", run_id)
        client.download_artifacts(
            run_id=run_id,
            path=mlflow_filepath,
            dst_path=local_dir
        )
        # scaler_path = download_online_file(
        #     scaler_uri, "scaler.pkl") if mode == 'remote' else scaler_uri
        scaler = load_local_pkl_as_object(
            os.path.join(local_dir, mlflow_filepath))
    else:
        scaler = load_local_pkl_as_object(scaler_uri)
    return scaler

def load_ts_id(load_ts_id_uri=None, mode="remote"):

    import tempfile

    if load_ts_id_uri is None:
        print("\nNo ts id list loaded.")
        return None

    if mode == "remote":
        run_id = load_ts_id_uri.split("/")[-2]
        mlflow_filepath = load_ts_id_uri.split("/artifacts/")[1]

        client = mlflow.tracking.MlflowClient()
        local_dir = tempfile.mkdtemp()
        print("ts id list: ", load_ts_id_uri)
        print("Run: ", run_id)
        client.download_artifacts(
            run_id=run_id,
            path=mlflow_filepath,
            dst_path=local_dir
        )
        ts_id_l = load_local_pkl_as_object(
            os.path.join(local_dir, mlflow_filepath))
    else:
        ts_id_l = load_local_pkl_as_object(load_ts_id_uri)
    return ts_id_l


def truth_checker(argument):
    """ Returns True if string has specific truth values else False"""
    return argument.lower() in ['true', '1', 't', 'y', 'yes', 'yeah', 'on']


def none_checker(argument):
    """ Returns True if string has specific truth values else False"""
    if argument is None:
        return None
    if type(argument) == str and argument.lower() in ['none', 'nope', 'nan', 'na', 'null', 'nope', 'n/a', 'mlflow_artifact_uri']:
        return None
    else:
        return argument


def load_artifacts(run_id, src_path, dst_path=None):
    import tempfile
    import os
    import mlflow
    if dst_path is None:
        dst_dir = tempfile.mkdtemp()
    else:
        dst_dir = os.path.sep.join(dst_path.split("/")[-1])
        os.makedirs(dst_dir, exist_ok=True)
    fname = src_path.split("/")[-1]
    return mlflow.artifacts.download_artifacts(artifact_path=src_path, dst_path="/".join([dst_dir, fname]), run_id=run_id)


def load_local_model_as_torch(local_path):
    import torch
    device = torch.device(
        'cuda') if torch.cuda.is_available() else torch.device('cpu')
    model = torch.load(local_path, map_location=device)
    model.device = device
    return model

def get_weather_covariates(start, end, fields=["shortwave_radiation"], name="W6 positive_active", inference=False):
    if type(fields) == str:
        fields = [fields]
    req_fields = ",".join(fields)
    if inference:
        print("here")
        result = requests.get(
            f"https://api.open-meteo.com/v1/forecast?latitude=42.564&longitude=12.643&hourly={req_fields}&forecast_days=10&timezone=auto"
        ).text
        result = json.loads(result)
        df_list = []
        for field in fields:
            data = result['hourly'][field]
            index = pd.to_datetime(result['hourly']['time'])
            assert len(data) == len(index)
            df = pd.DataFrame(data=data, index=index, columns=[field]).asfreq("60min")
            df.index.name = "Datetime"
            df_list.append(df)
        print("END", df_list)
        if name in ["W6 positive_active", "W6 positive_reactive"]:
            result_db = requests.get(
            f"http://38.242.137.200:8000/api/v1/query?source=hourly_forecast&coordinates=(42.569,%2012.608)&start_date={start}&end_date={end}&fields={req_fields}"
            ).text
        elif name in ["W4 positive_active", "W4 positive_reactive"]:
            result_db = requests.get(
                f"http://38.242.137.200:8000/api/v1/query?source=hourly_forecast&coordinates=(42.567,%2012.607)&start_date={start}&end_date={end}&fields={req_fields}"
            ).text
        else:
            result_db = requests.get(
                f"http://38.242.137.200:8000/api/v1/query?source=hourly_forecast&coordinates=(42.564,%2012.643)&start_date={start}&end_date={end}&fields={req_fields}"
            ).text
        result_db = json.loads(result_db)
        df_list_db = []
        for field in fields:
            data = result_db['results'][field]['value']
            index = pd.to_datetime(result_db['time'])
            assert len(data) == len(index)
            df = pd.DataFrame(data=data, index=index, columns=[field]).asfreq("60min")
            df.index.name = "Datetime"
            df_list_db.append(df)
        print("START", df_list_db)
        result = []
        for ts, ts_db in zip(df_list, df_list_db):
            print("TS_DB", ts_db)
            ts = ts[ts.index > ts_db.index[-1]]
            print("TS", ts)
            result_df = pd.concat([ts_db, ts])
            print(result_df)
            result.append(result_df)

        return result
    else:
        start = start.strftime("%Y-%m-%d")
        end = end.strftime("%Y-%m-%d")
        if name in ["W6 positive_active", "W6 positive_reactive"]:
            result = requests.get(
            f"http://38.242.137.200:8000/api/v1/query?source=hourly_forecast&coordinates=(42.569,%2012.608)&start_date={start}&end_date={end}&fields={req_fields}"
            ).text
        elif name in ["W4 positive_active", "W4 positive_reactive"]:
            result = requests.get(
                f"http://38.242.137.200:8000/api/v1/query?source=hourly_forecast&coordinates=(42.567,%2012.607)&start_date={start}&end_date={end}&fields={req_fields}"
            ).text
        else:
            result = requests.get(
                f"http://38.242.137.200:8000/api/v1/query?source=hourly_forecast&coordinates=(42.564,%2012.643)&start_date={start}&end_date={end}&fields={req_fields}"
            ).text
        result = json.loads(result)
        df_list = []
        for field in fields:
            data = result['results'][field]['value']
            index = pd.to_datetime(result['time'])
            assert len(data) == len(index)
            df = pd.DataFrame(data=data, index=index, columns=[field]).asfreq("60min")
            df.index.name = "Datetime"
            df_list.append(df)
        return df_list



def load_local_csv_as_darts_timeseries(local_path, name='Time Series', time_col='Datetime', last_date=None, multiple = False, day_first=True, resolution="15"):

    import logging
    import darts
    import numpy as np
    import pandas as pd

    try:
        if multiple:
            #TODO Fix this too
            ts_list, id_l, ts_id_l = multiple_ts_file_to_dfs(series_csv=local_path, day_first=True, resolution=resolution)
            covariate_l  = []
            #print("liiiist", local_path)
            #print(ts_list[0])
            print("\nTurning dataframes to timeseries...")
            logging.info("\nTurning dataframes to timeseries...")
            for comps in tqdm(ts_list):
                first = True
                for df in comps:
                    covariates = darts.TimeSeries.from_dataframe(
                                df,
                                fill_missing_dates=True,
                                freq=None)
                    covariates = covariates.astype(np.float32)
                    if last_date is not None:
                        #print(last_date)
                        try:
                            covariates.drop_after(pd.Timestamp(last_date))
                        except:
                            pass
                    if first:
                        first = False
                        covariate_l.append(covariates)
                    else:
                        covariate_l[-1] = covariate_l[-1].stack(covariates)
            covariates = covariate_l
        else:
            id_l, ts_id_l = [[]], [[]]
            covariates = darts.TimeSeries.from_csv(
                local_path, time_col=time_col,
                fill_missing_dates=True,
                freq=None)
            covariates = covariates.astype(np.float32)
            if last_date is not None:
                try:
                    covariates.drop_after(pd.Timestamp(last_date))
                except:
                    pass
#=======
#        covariates = darts.TimeSeries.from_csv(
#            local_path, time_col=time_col,
#            fill_missing_dates=True,
#            freq=None)
#        covariates = covariates.astype(np.float32)
#        if last_date is not None:
#            covariates.drop_after(pd.Timestamp(last_date))
#>>>>>>> dev
    except (FileNotFoundError, PermissionError) as e:
        print(
            f"\nBad {name} file.  The model won't include {name}...")
        logging.info(
            f"\nBad {name} file. The model won't include {name}...")
        covariates = None
    print("NUM NULL AFTER APPEND", covariates[-1].pd_dataframe().isnull().sum().sum())
    return covariates, id_l, ts_id_l


def parse_uri_prediction_input(model_input: dict, model, ts_id_l) -> dict:

    series_uri = model_input['series_uri']

    # str to int
    batch_size = int(model_input["batch_size"])
    roll_size = int(model_input["roll_size"])
    forecast_horizon = int(model_input["n"])

    multiple = truth_checker(model_input["multiple"])
    weather_covariates = none_checker(model_input["weather_covariates"])
    resolution = model_input["resolution"]
    ts_id_pred = model_input["ts_id_pred"]
    #multiple, resolution and weather_covariates now compulsory

    ## Horizon
    n = int(
        model_input["n"]) if model_input["n"] is not None else model.output_chunk_length
    roll_size = int(
        model_input["roll_size"]) if model_input["roll_size"] is not None else model.output_chunk_length

    ## TODO: future and past covariates (load and transform to darts)
    past_covariates_uri = model_input["past_covariates_uri"]
    future_covariates_uri = model_input["future_covariates_uri"]

    batch_size = int(model_input["batch_size"]
                     ) if model_input["batch_size"] is not None else 1

    if 'runs:/' in series_uri or 's3://mlflow-bucket/' in series_uri or series_uri.startswith('http://'):
        print('\nDownloading remote file of recent time series history...')
        series_uri = download_mlflow_file(series_uri)

    predict_series_idx = [elem[0] for elem in ts_id_l].index(ts_id_pred)

    if "history" not in model_input:
        history, id_l, ts_id_l_series = load_local_csv_as_darts_timeseries(
            local_path=series_uri,
            name='series',
            time_col='Datetime',
            last_date=None,
            multiple=multiple,
            resolution=model_input["resolution"] )

        
        if multiple:
             idx = [elem[0] for elem in ts_id_l_series].index(ts_id_pred)
             history = [history[idx]]
        else:
            #TODO Fix multivariate
            history = [history]
    else:
            history = darts.TimeSeries.from_dataframe(
                model_input["history"],
                fill_missing_dates=True,
                freq=None)
            history = [history.astype(np.float32)]

    if none_checker(future_covariates_uri) is not None:
        pass
    #TODO
    else:
        future_covariates = None

    if none_checker(past_covariates_uri) is not None:
        pass
    else:
        past_covariates = None

    if weather_covariates:
        #TODO Fix that
        covs_nans = get_weather_covariates(history[0].pd_dataframe().index[0], 
                                           pd.Timestamp(date.today()).ceil(freq='D') + pd.Timedelta("10D"), 
                                           weather_covariates,
                                           inference=True)
        print(covs_nans)
        covs = []
        for cov in covs_nans:
            covs.append(cov.asfreq('60min').interpolate(inplace=False, method='time').ffill())
            print(cov)
        future_covariates = darts.TimeSeries.from_dataframe(
            covs[0])
        
        for cov in covs[1:]:
            future_covariates = future_covariates.stack(darts.TimeSeries.from_dataframe(
                cov))
        future_covariates = [future_covariates]

    return {
        "n": n,
        "history": history,
        "roll_size": roll_size,
        "future_covariates": future_covariates,
        "past_covariates": past_covariates,
        "batch_size": batch_size,
        "predict_series_idx": predict_series_idx,
    }

def multiple_ts_file_to_dfs(series_csv: str = "../../RDN/Load_Data/2009-2019-global-load.csv",
                            day_first: bool = True,
                            resolution: str = "15",
                            value_name="Value"):
    """
    Reads the input multiple ts file, and returns a tuple containing a list of the time series it consists
    of, along with their ids and timeseries ids. 

    Parameters
    ----------
    series_csv
        The file name of the csv to be read. It must be in the multiple ts form described in the documentation
    day_first
        Wether the day appears before the month in dates
    resolution
        The resolution of the dataset
    value_name
        The name of the value column of the returned dataframes

    Returns
    -------
    Tuple[List[List[pandas.DataFrame]], List[List[str]], List[List[str]]]
        A tuple with the list of lists of dataframes to be returned, the ids 
        of their components, and the timeseries ids. For example, if the function
        reads a file with 2 time series (with ids ts_1 and ts_2), and each one 
        consists of 3 components (with ids ts_1_1, ts_1_2, ts_1_3, ts_2_1, ts_2_2, ts_2_3),
        then the function will return:
        (res, id_l, ts_id_l), where:
        res = [[ts_1_comp_1, ts_1_comp_2, ts_1_comp_3], [ts_2_comp_1, ts_2_comp_2, ts_2_comp_3]]
        id_l = [[ts_1_1, ts_1_2, ts_1_3], [ts_2_1, ts_2_2, ts_2_3]]
        ts_id_l = [[ts_1, ts_1, ts_1], [ts_2, ts_2, ts_2]]
        All of the above lists of lists have the same number of lists and each sublist the same
        amount of elements as the sublist of any other list of lists in the corresponding location.
        This is true because each sublist corresponds to a times eries, and each element of this
        sublist corresponds to a component of this time series.
    """

    ts = pd.read_csv(series_csv,
                     sep=None,
                     header=0,
                     index_col=0,
                     parse_dates=True,
                     dayfirst=day_first,
                     engine='python')
    #print("ts", ts, sep="\n")
    res = []
    id_l = []
    ts_id_l = []
    ts_ids = list(np.unique(ts["Timeseries ID"]))
    print("\nTurning multiple ts file to dataframe list...")
    logging.info("\nTurning multiple ts file to dataframe list...")
    for ts_id in tqdm(ts_ids):
        curr_ts = ts[ts["Timeseries ID"] == ts_id]
        ids = list(np.unique(curr_ts["ID"]))
        res.append([])
        id_l.append([])
        ts_id_l.append([])
        for id in ids:
            curr_comp = curr_ts[curr_ts["ID"] == id]
            curr_comp = pd.melt(curr_comp, id_vars=['Date', 'ID', 'Timeseries ID'], var_name='Time', value_name="Value")
            curr_comp["Datetime"] = pd.to_datetime(curr_comp['Date'] + curr_comp['Time'], format='%Y-%m-%d%H:%M:%S')
            curr_comp = curr_comp.set_index("Datetime")
            series = curr_comp[value_name].sort_index().dropna().asfreq(resolution+'min')
            res[-1].append(pd.DataFrame({value_name : series}))
            id_l[-1].append(id)
            ts_id_l[-1].append(ts_id)
    return res, id_l, ts_id_l

def multiple_dfs_to_ts_file(res_l, id_l, ts_id_l, save_dir, save=True):
    ts_list = []

    print("\nTurning dataframe list to multiple ts file...")
    logging.info("\nTurning dataframe list to multiple ts file...")
    for ts_num, (ts, id_ts, ts_id_ts) in tqdm(list(enumerate(zip(res_l, id_l, ts_id_l)))):
#        print("ts_num", ts)
        if type(ts) == darts.timeseries.TimeSeries:
            ts = [ts.univariate_component(i).pd_dataframe() for i in range(ts.n_components)]
        for comp_num, (comp, id, ts_id) in enumerate(zip(ts, id_ts, ts_id_ts)):
 #           print(comp)
            load_col = comp.columns[0]
            print(comp.index)
            comp["Date"] = comp.index.date
            comp["Time"] = comp.index.time
            comp = pd.pivot_table(comp, index=["Date"], columns=["Time"])
            print(comp, load_col)
            comp = comp[load_col]
            comp["ID"] = id
            comp["Timeseries ID"] = ts_id
            ts_list.append(comp)
    res = pd.concat(ts_list).sort_values(by=["Date", "ID"])
    columns = list(res.columns)[-2:] + list(res.columns)[:-2]
    res = res[columns].reset_index()
    if save:
        res.to_csv(save_dir)
    return res


def check_mandatory(argument, argument_name, mandatory_prerequisites):
    if none_checker(argument) is None:
        raise MandatoryArgNotSet(argument_name, mandatory_prerequisites)

#epestrepse kai IDs
#prwta psakse ID meta SC
#TODO: Fix it. It does not get any progress any more
# def get_training_progress_by_tag(fn, tag):
#     # assert(os.path.isdir(output_dir))

#     image_str = tf.compat.v1.placeholder(tf.string)

#     im_tf = tf.image.decode_image(image_str)

#     sess = tf.compat.v1.InteractiveSession()
#     with sess.as_default():
#         count = 0
#         values = []
#         for e in summary_iterator(fn):
#             for v in e.summary.value:
#                 if tag == v.tag:
#                     values.append(v.simple_value)
#     sess.close()
#     return {"Epoch": range(1, len(values) + 1), "Value": values}

# def log_curves(tensorboard_event_folder, output_dir='training_curves'):
    # TODO: fix deprecation warnings

    # tf.compat.v1.disable_eager_execution()

    # # locate tensorboard event file
    # event_file_names = os.listdir(tensorboard_event_folder)
    # if len(event_file_names) > 1:
    #     logging.info(
    #         "Searching for term 'events.out.tfevents.' in logs folder to extract tensorboard file...\n")
    #     print(
    #         "Searching for term 'events.out.tfevents.' in logs folder to extract tensorboard file...\n")
    # tensorboard_folder_list = os.listdir(tensorboard_event_folder)
    # event_file_name = [fname for fname in tensorboard_folder_list if
    #     "events.out.tfevents." in fname][0]
    # tensorboard_event_file = os.path.join(tensorboard_event_folder, event_file_name)

    # # test for get_training_progress_by_tag
    # print(tensorboard_event_file)

    # # local folder
    # print("Creating local folder to store the datasets as csv...")
    # logging.info("Creating local folder to store the datasets as csv...")
    # os.makedirs(output_dir, exist_ok=True)

    # # get metrix and store locally
    # training_loss = pd.DataFrame(get_training_progress_by_tag(tensorboard_event_file, 'training/loss_total'))
    # training_loss.to_csv(os.path.join(output_dir, 'training_loss.csv'))

    # # testget_training_progress_by_tag
    # print(training_loss)

    # ## consider here nr_epoch_val_period
    # validation_loss = pd.DataFrame(get_training_progress_by_tag(tensorboard_event_file, 'validation/loss_total'))

    # # test for get_training_progress_by_tag
    # print(validation_loss)
    # print(validation_loss.__dict__)

    # validation_loss["Epoch"] = (validation_loss["Epoch"] * int(len(training_loss) / len(validation_loss)) + 1).astype(int)
    # validation_loss.to_csv(os.path.join(output_dir, 'validation_loss.csv'))

    # learning_rate = pd.DataFrame(get_training_progress_by_tag(tensorboard_event_file, 'training/learning_rate'))
    # learning_rate.to_csv(os.path.join(output_dir, 'learning_rate.csv'))

    # sns.lineplot(x="Epoch", y="Value", data=training_loss, label="Training")
    # sns.lineplot(x="Epoch", y="Value", data=validation_loss, label="Validation", marker='o')
    # plt.grid()
    # plt.legend()
    # plt.title("Loss")
    # plt.savefig(os.path.join(output_dir, 'loss.png'))

    # plt.figure()
    # sns.lineplot(x="Epoch", y="Value", data=learning_rate)
    # plt.grid()
    # plt.title("Learning rate")
    # plt.savefig(os.path.join(output_dir, 'learning_rate.png'))

    # print("Uploading training curves to MLflow server...")
    # logging.info("Uploading training curves to MLflow server...")
    # mlflow.log_artifacts(output_dir, output_dir)

    # print("Artifacts uploaded. Deleting local copies...")
    # logging.info("Artifacts uploaded. Deleting local copies...")
    # shutil.rmtree(output_dir)
