import mlflow

def MLflowDartsModelPredict(pyfunc_model_folder, model_input):
    """This is the main function for predicting MLflow pyfunc models. The inputs are csv file uris (online or local) and integers. 
    The csv files are dowloaded and the converted to darts.TimeSeries and finally given to the loaded models and for prediction according to their 
    specification"""

    with mlflow.start_run(run_name='inference') as mlrun:


        input = {
            "n": model_input["n"],
            "series_uri": model_input["series_uri"],
            "roll_size": "1",
            "future_covariates_uri": "None",
            "past_covariates_uri": "None",
            "batch_size": "1",
            "multiple": "False",
            "weather_covariates": "None",
            "resolution": "60",
            "ts_id_pred": model_input["ts_id_pred"],
        }

        # Load model as a PyFuncModel.
        print("\nLoading pyfunc model...")
        loaded_model = mlflow.pyfunc.load_model("../")

        # Predict on a Pandas DataFrame.
        print("\nPyfunc model prediction...")
        predictions = loaded_model.predict(input)

        return predictions
