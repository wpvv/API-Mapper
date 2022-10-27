import itertools
import json
import re

import joblib
import matplotlib.pyplot as plt
import numpy
import pandas as pd
import seaborn as sns
import tensorflow
from imblearn.over_sampling import RandomOverSampler
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from pandarallel import pandarallel
from sentence_transformers import SentenceTransformer
from sklearn import model_selection, feature_selection, linear_model, ensemble, metrics

import ApplicationConfig
import ConnectionConfig
import JsonGlue

abbreviations = {
    "id": "identifier",
    "v": "version",
    "txt": "text",
    "amount": "amt",
    "description": "desc",
    "name": "nm",
    "number": "num",
    "quantity": "qty"
}

additional_stopwords = [
    "identifier",
    "version",
    "public",
    "private",
    "api",
]


def lemmatizer(word: str) -> str:
    """ Function to lemmatize a given word

    This function will stem and give a more used alternative for the given word
    It will also check if a common API related abbreviation is used and replace it with the full word

    :param word: string to lemmatize
    :return: lemmatized checked for abbreviations word
    """
    lemmatizer = WordNetLemmatizer()
    word = lemmatizer.lemmatize(word)
    if word in abbreviations:
        return abbreviations[word]
    return word


def string_preprocessing(value: str) -> str:
    """ Function to preprocces a given string

    This function will remove all stopwords if it exists in the NLTK stopword list.
    It will also remove any special characters, extra spaces and will use the lemmatizer
    to return a string of lemmatized words.
    :param value: string of words to process
    :return: string of consisting of lowercase lemmatized words, free of extra spaces, special characters
    """
    stop_words = list(stopwords.words("english"))
    if not isinstance(value, str):
        return None
    return_value = re.sub("[^A-Za-z]+", " ", value.lower())
    return_value = re.sub(" +", " ", return_value)
    value = word_tokenize(return_value)
    return_value_list = [lemmatizer(word) for word in value if word not in stop_words + additional_stopwords]
    return " ".join(map(str, return_value_list))


def get_response_schema(spec: dict) -> dict:
    """ Get the response schema from an OpenAPI document

    This function gets the response schema from a OpenAPI document, if the schema is a JSON document and the schema is
    used for an HTTP 200 response.

    :param spec: an API element in an OpenAPI document
    :return: JSON response schema
    """
    if "responses" in spec:
        if "200" in spec["responses"]:
            if "content" in spec["responses"]["200"]:
                for key, value in spec["responses"]["200"]["content"].items():
                    if "/" in key and key.startswith("application/json") and "schema" in value:
                        return value["schema"]
    return {}


def get_request_schema(spec: dict) -> dict:
    """ Get the request schema from an API in an penAPI document

    This function will extract the request schema from an API if the schema is of type JSON

    :param spec: an API element in an OpenAPI document
    :return: JSON request schema
    """
    if "requestBody" in spec:
        if "content" in spec["requestBody"]:
            for key, value in spec["requestBody"]["content"].items():
                if "/" in key and key.startswith("application/json") and "schema" in value:
                    return value["schema"]
    return {}


def get_description_and_summary(spec: dict, preprocessing: bool = True) -> str:
    """ Function to extract the summary and description

    This function will extract a description from an API element of an OpenAPI document. This description can consist
    of either an API description or an API summary or both. The function also has the option to use the preprocessing to
    generate a description suitable for NLP.
    :param spec: an API element in an OpenAPI document
    :param preprocessing: Boolean to indicate preprocessing is needed
    :return: a description of the API
    """
    return_string = ""
    if "summary" in spec:
        return_string += spec["summary"]
    if "description" in spec:
        return_string += spec["description"]
    if preprocessing:
        return string_preprocessing(return_string)
    else:
        return return_string


def get_operation_compatibility(operations: tuple) -> int:
    """ Function to determine if the operations of a pair of APIs are suitable for a connection

    This function checks whether the pair of APIs are suitable for a connection within the current mapping
    framework. The current way of working expects a source (GET) and a target (POST, PUT or DELETE), all other connections
    are incompatible

    :param operations: tuple of operations from the 2 APIs
    :return: 1 if compatible, 0 if incompatible, integer because of use in dataframe... TODO
    """
    supported_types = ["post", "put", "delete"]
    if operations[0] == "get":
        return int(operations[1] in supported_types)
    elif operations[1] == "get":
        return int(operations[0] in supported_types)
    else:
        return 0


def set_operation_compatibility(df_row: dict) -> dict:
    """ Function to set a humanreadable identifier (name) and to set the operation compatibility

    This function sets a humanreadable identifier for the purpose of easier identification during manual labelling. It
    also calls the get_operation_compatibility() to extract the compatibility of the connection and sets the value.
    :param df_row: row of the generated dataframe
    :return: modified row of teh dataframe, modified that it contains a name and an int representing compatibility
    """
    df_row["name"] = df_row["application1_operation"] + ":" + df_row["application1_path"] + " - " + df_row[
        "application2_operation"] + ":" + df_row["application2_path"]
    df_row["supported_connection"] = get_operation_compatibility(
        (df_row["application1_operation"], df_row["application2_operation"]))
    return df_row


def calculate_similarity_scores(model: object, df_row: dict, training: bool = False) -> dict:
    """ Function to generate the similarity features

     This function generates the similarity scores for both the path and description similarity features. It uses
     a given model (BERT sentence encoding) to encode the path and description of both APIs in a row and gives a score
     calculated with the cosine distance between the encoded messages. This cosine distance is called the similarity
     score.

    :param model: instance of BERT sentence encoding
    :param df_row: row of the generated dataframe
    :param training: boolean to indicate whether to print progress info
    :return: a modified row, now with the 2 similarity scores appended
    """
    if training:
        print("calculating similarity_scores, :", df_row.name)
    for similarity_type in ["path", "description"]:
        messages = [df_row["application1_" + similarity_type],
                    df_row["application2_" + similarity_type]]
        message_embeddings = model.encode(messages)
        a = tensorflow.make_ndarray(
            tensorflow.make_tensor_proto(message_embeddings))  # storing the vector in the form of numpy array
        cos_sim = numpy.dot(a[0], a[1]) / (
                numpy.linalg.norm(a[0]) * numpy.linalg.norm(a[1]))  # Finding the cosine between the two vectors
        df_row["similarity_score_" + similarity_type] = cos_sim

    return df_row


def calculate_json_glue_scores(df_row: dict) -> dict:
    """ Function to generate the schema distance features

    This function calls the JsonGlue library to give a distance between the 2 schemas of the APIs.
    Both an edit distance and a lexical distance is calculated.
    For more infor:
    "JSONGlue: A hybrid matcher for JSON schema matching" by Vitor Marini Blaselbauer & Jõao Marcelo Borovina Josko

    :param df_row: row of the generated dataframe
    :return: a modified row, now with the 2 schema distance features appended
    """
    jsonglue_scores = JsonGlue.calculate_json_glue_score(df_row["application1_schema"],
                                                         df_row["application2_schema"])
    df_row["schema_edit"] = jsonglue_scores["edit_average"]
    df_row["schema_lexical"] = jsonglue_scores["lexical_average"]
    df_row["label"] = 0
    return df_row


def create_data_set(application_ids=None, training=False):
    """ Function to generate a data set from all the configured application in the framework in the case of a training
    session. In case it is not a training it wil generate a data set based on a pair of given applications.
    It will gather all APIs from the applications, preprocess the data of those APIs and use Cartesian product to give
    all the relevant possible connections. In case of a training connections within an application are allowed,
    otherwise it is not.
    :param application_ids: list of application to generate a data set on
    :param training: boolean to indicate a training session
    :return: a dataset for either testing and training or a dataset for a prediction
    """
    if training:
        applications = ApplicationConfig.get_application_configs(internal=True)
    elif application_ids:
        applications = [ApplicationConfig.get_application_config(application_id, internal=True) for application_id in
                        application_ids]
    else:
        return
    model = SentenceTransformer("bert-base-nli-mean-tokens")
    endpoint_id = None
    if training:
        pandarallel.initialize(progress_bar=True)
    else:
        pandarallel.initialize()
    apis = []
    for application in applications:
        specs = ConnectionConfig.get_application_specs(application["id"])
        if not training:
            endpoint_id = 1
        for path in specs["paths"]:
            for operation in specs["paths"][path]:
                temp_spec = specs["paths"][path][operation]
                api_data = {"name": application["name"],
                            "path": string_preprocessing(path),
                            "operation": operation,
                            "original_description": get_description_and_summary(temp_spec, preprocessing=False),
                            "description": get_description_and_summary(temp_spec)}
                if operation == "get":
                    api_data["schema"] = json.dumps(get_response_schema(temp_spec))
                else:
                    api_data["schema"] = json.dumps(get_request_schema(temp_spec))
                if not training and endpoint_id is not None:
                    api_data["id"] = application["id"]
                    api_data["endpoint_id"] = endpoint_id
                    api_data["original_path"] = path
                    api_data["server_override"] = "" if "servers" not in temp_spec else temp_spec["servers"][0]["url"]
                    endpoint_id += 1
                apis.append(api_data)
    data_combinations = list(itertools.combinations(apis, 2))
    normalised_list = []
    for element in data_combinations:
        row = {}
        for index, tuple_item in enumerate(element):
            row.update({"application" + str(index + 1) + "_" + str(key): val for key, val in tuple_item.items()})
        normalised_list.append(row)
    data_set = pd.DataFrame(normalised_list)
    if not training:
        data_set = data_set.loc[data_set["application1_id"] != data_set["application2_id"]]
    data_set = data_set.apply(lambda df_row: set_operation_compatibility(df_row), axis=1)
    data_set = data_set.loc[data_set["supported_connection"] == 1]
    data_set = data_set.apply(lambda df_row: calculate_similarity_scores(model, df_row, training=training), axis=1)
    data_set = data_set.parallel_apply(lambda df_row: calculate_json_glue_scores(df_row), axis=1)
    data_set.drop(["supported_connection", "label"], axis=1, inplace=True)
    data_set = data_set.set_index("name")
    if training:
        data_set.to_csv("data/gradient_boosting/chat.csv")
        print("Data set written to data/gradient_boosting/chat.csv")
    return data_set


def read_training_data_set(make_graphs: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """ Function to read previously generated and manually labelled dataset.

    This function reads a previously generated and labelled dataset.
    It the splits the data in 70% for training and the reaming 30% for testing purposes.
    It then uses random oversampling to balance the training dataset,
    this is to prevent a bias towards a certain label based on the amount of occurrences of that label.


    :param make_graphs: boolean to generate graphs depicting the feature performances
    :return: a tuple containing the entire dataset, the training dataset and the test dataset
    """
    data_set = pd.read_csv("chat_labeled.csv")
    data_set_copy = data_set
    data_set.drop(
        ["Unnamed: 0", "application1_name", "application1_path", "application2_name",
         "application2_path", "application1_schema", "application2_schema",
         "application1_operation", "application2_operation", "application1_description", "application2_description",
         "application1_original_description", "application2_original_description"
         ], axis=1, inplace=True)
    data_set = data_set.set_index("name")
    data_set_copy = data_set_copy.set_index("name")
    train_data, test_data = model_selection.train_test_split(data_set,
                                                             test_size=0.3, random_state=1)
    sm = RandomOverSampler(random_state=1)
    # Fit the model to generate the data.
    x_train, y_train = sm.fit_resample(train_data.drop("label", axis=1), train_data["label"])
    train_data = pd.concat([pd.DataFrame(y_train), pd.DataFrame(x_train)], axis=1)
    train_data.columns = data_set.columns
    print(train_data.head)
    print("x_train shape:", train_data.drop("label", axis=1).shape, "| X_test shape:",
          test_data.drop("label", axis=1).shape)
    print("Label train mean:", numpy.mean(train_data["label"]).round(2), "| label test mean:",
          numpy.mean(test_data["label"]).round(2))
    if make_graphs:
        create_feature_graphs(data_set, train_data)
    return data_set_copy, train_data, test_data


def create_feature_graphs(data_set: pd.DataFrame, train_data: pd.DataFrame) -> None:
    """ Function to generate graphs about the performance of the features.

    Only for writing purposes

    :param data_set: entire dataset
    :param train_data: part of the dataset for training purposes
    """
    x_train = train_data.drop("label", axis=1).values
    y_train = train_data["label"].values

    matrix = data_set.corr().round(2)
    sns.heatmap(matrix, annot=True, cmap="YlGnBu", cbar=True, linewidths=0.5)
    plt.title("Correlation Matrix")

    plt.savefig("data/correlation.png", bbox_inches="tight", dpi=100)
    plt.clf()

    feature_names = train_data.drop("label", axis=1).columns
    selector = feature_selection.SelectKBest(score_func=
                                             feature_selection.f_classif, k=4).fit(x_train, y_train)
    anova_selected_features = feature_names[selector.get_support()]

    selector = feature_selection.SelectFromModel(estimator=
                                                 linear_model.LogisticRegression(C=1, penalty="l1",
                                                                                 solver="liblinear"),
                                                 max_features=4).fit(
        x_train, y_train)
    lasso_selected_features = feature_names[selector.get_support()]

    dtf_features = pd.DataFrame({"features": feature_names})
    dtf_features["anova"] = dtf_features["features"].apply(lambda x: "anova" if x in anova_selected_features else "")
    dtf_features["num1"] = dtf_features["features"].apply(lambda x: 1 if x in anova_selected_features else 0)
    dtf_features["lasso"] = dtf_features["features"].apply(lambda x: "lasso" if x in lasso_selected_features else "")
    dtf_features["num2"] = dtf_features["features"].apply(lambda x: 1 if x in lasso_selected_features else 0)
    dtf_features["method"] = dtf_features[["anova", "lasso"]].apply(lambda x: (x[0] + " " + x[1]).strip(), axis=1)
    dtf_features["selection"] = dtf_features["num1"] + dtf_features["num2"]
    sns.barplot(y="features", x="selection", hue="method", data=dtf_features.sort_values("selection", ascending=False),
                dodge=False)
    plt.title("Lasso regularization")
    plt.savefig("data/lasso_reg.png", bbox_inches="tight", dpi=100)
    plt.clf()

    feature_names = train_data.drop("label", axis=1).columns.tolist()
    model = ensemble.RandomForestClassifier(n_estimators=100,
                                            criterion="entropy", random_state=0)
    model.fit(x_train, y_train)
    feature_importance = model.feature_importances_
    dtf_feature_importance = pd.DataFrame({"IMPORTANCE": feature_importance * 100,
                                           "VARIABLE": feature_names}).sort_values("IMPORTANCE",
                                                                                   ascending=False)
    dtf_feature_importance["cumsum"] = dtf_feature_importance["IMPORTANCE"].cumsum(axis=0)
    dtf_feature_importance = dtf_feature_importance.set_index("VARIABLE")

    fig, ax = plt.subplots(1, 2)
    fig.suptitle("Feature importance", fontsize=20)

    ax[0].title.set_text("Per variable")
    dtf_feature_importance[["IMPORTANCE"]].plot(kind="bar", legend=False, ax=ax[0]).grid(axis="y")
    ax[0].set(xlabel="", xticks=numpy.arange(len(dtf_feature_importance)),
              xticklabels=dtf_feature_importance.index, ylabel="importance (%)")

    ax[0].tick_params(axis="x", labelrotation=70)

    ax[1].title.set_text("Cumulative")
    dtf_feature_importance[["cumsum"]].plot(kind="line", linewidth=4, legend=False, ax=ax[1],
                                            yticks=numpy.arange(0, 120, step=20))
    ax[1].set(xlabel="", ylabel="importance (%)", xticks=numpy.arange(len(dtf_feature_importance)),
              xticklabels=dtf_feature_importance.index)
    ax[1].tick_params(axis="x", labelrotation=70)

    plt.grid(axis="both")
    plt.tight_layout()
    plt.savefig("data/importance.png", bbox_inches="tight", dpi=100)
    plt.clf()


def create_model_graphs(model: object, x_train: pd.DataFrame, y_train: pd.DataFrame, x_test: pd.DataFrame,
                        y_test: pd.DataFrame, predicted: list, predicted_prob: list, recall: list,
                        precision: list) -> None:
    """ Function to generate graphs about the performance of the generated model

    Only for writing purposes

    :param model: instance of boosting gradient classifier
    :param x_train: features from part of the dataset for training purposes
    :param y_train: label from part of the dataset for training purposes
    :param x_test: features form part of the dataset for testing purposes
    :param y_test: label from part of the dataset for testing purposes
    :param predicted: list of predictions as 0 or 1
    :param predicted_prob: list of predictions between 0, 1
    :param recall: recall score
    :param precision: precision score
    """
    classes = [0, 1]
    fig, ax = plt.subplots()
    cm = metrics.confusion_matrix(y_test, predicted, labels=classes)
    sns.heatmap(cm, annot=True, fmt="d", cmap=plt.cm.Blues, cbar=False)
    ax.set(xlabel="Predicted", ylabel="True", title="Confusion matrix")
    ax.set_yticklabels(labels=classes, rotation=0)
    plt.savefig("data/confusion.png", bbox_inches="tight", dpi=100)
    plt.clf()

    fig, ax = plt.subplots(nrows=1, ncols=2)  # plot ROC curve
    fpr, tpr, thresholds = metrics.roc_curve(y_test, predicted_prob)
    roc_auc = metrics.auc(fpr, tpr)
    ax[0].plot(fpr, tpr, color="darkorange", lw=3, label="area = %0.2f" % roc_auc)
    ax[0].plot([0, 1], [0, 1], color="navy", lw=3, linestyle="--")
    ax[0].hlines(y=recall, xmin=0, xmax=1 - cm[0, 0] / (cm[0, 0] + cm[0, 1]), color="red", linestyle="--", alpha=0.7,
                 label="chosen threshold")
    ax[0].vlines(x=1 - cm[0, 0] / (cm[0, 0] + cm[0, 1]), ymin=0, ymax=recall, color="red", linestyle="--", alpha=0.7)
    ax[0].set(xlabel="False Positive Rate", ylabel="True Positive Rate (Recall)",
              title="Receiver operating characteristic")
    ax[0].legend(loc="lower right")
    ax[0].grid(True)  # annotate ROC thresholds
    threshold = []
    for i, t in enumerate(thresholds):
        t = numpy.round(t, 1)
        if t not in threshold:
            ax[0].annotate(t, xy=(fpr[i], tpr[i]), xytext=(fpr[i], tpr[i]),
                           textcoords="offset points", ha="left", va="bottom")
            threshold.append(t)
    precisions, recalls, thresholds = metrics.precision_recall_curve(y_test, predicted_prob)
    roc_auc = metrics.auc(recalls, precisions)
    ax[1].plot(recalls, precisions, color="darkorange", lw=3, label="area = %0.2f" % roc_auc)
    ax[1].plot([0, 1], [(cm[1, 0] + cm[1, 0]) / len(y_test), (cm[1, 0] + cm[1, 0]) / len(y_test)], linestyle="--",
               color="navy", lw=3)
    ax[1].hlines(y=precision, xmin=0, xmax=recall, color="red", linestyle="--", alpha=0.7, label="chosen threshold")
    ax[1].vlines(x=recall, ymin=0, ymax=precision, color="red", linestyle="--", alpha=0.7)
    ax[1].set(xlabel="Recall", ylabel="Precision", title="Precision-Recall curve")
    ax[1].legend(loc="lower left")
    ax[1].grid(True)  # annotate P-R thresholds
    threshold = []
    for i, t in enumerate(thresholds):
        t = numpy.round(t, 1)
        if t not in threshold:
            ax[1].annotate(numpy.round(t, 1), xy=(recalls[i], precisions[i]),
                           xytext=(recalls[i], precisions[i]),
                           textcoords="offset points", ha="left", va="bottom")
            threshold.append(t)
    plt.savefig("data/pr_curves.png", bbox_inches="tight", dpi=100)
    plt.clf()

    dic_scores = {"threshold": [], "accuracy": [], "precision": [], "recall": [], "f1": []}
    predicted_prob = model.fit(x_train, y_train).predict_proba(x_test)[:, 1]
    for threshold in numpy.arange(0.1, 1, step=0.1):
        predicted = (predicted_prob > threshold)
        dic_scores["threshold"].append(threshold)
        dic_scores["accuracy"].append(metrics.accuracy_score(y_test, predicted))
        dic_scores["precision"].append(metrics.precision_score(y_test, predicted))
        dic_scores["recall"].append(metrics.recall_score(y_test, predicted))
        dic_scores["f1"].append(metrics.f1_score(y_test, predicted))
    dtf_scores = pd.DataFrame(dic_scores)
    dtf_scores = dtf_scores.set_index("threshold")
    dtf_scores.plot(title="Threshold Selection", ylabel="Scores")
    plt.savefig("data/threshold.png", bbox_inches="tight", dpi=100)
    plt.clf()


def train_model(x_train: pd.DataFrame, y_train: pd.DataFrame) -> object:
    """ Function to generate the best possible model in a fairly short time

    This function uses randomized search to find the best model, according to its F1 score, within the set of parameters
    for the given data.

    :param x_train: features of the 70% of the dataset for training purposes
    :param y_train: label of the 70% of the dataset for training purposes
    :return: found model that performs the best
    """
    model = ensemble.GradientBoostingClassifier()
    parameters = {"learning_rate": [0.3, 0.2, 0.15, 0.1, 0.05, 0.01, 0.005, 0.001],
                  "n_estimators": [100, 250, 500, 750, 1000, 2000, 3000, 4000, 5000],
                  "max_depth": [2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 50],
                  "min_samples_split": [2, 4, 6, 8, 10, 20, 40, 60, 100],
                  "min_samples_leaf": [1, 3, 5, 7, 9],
                  "max_features": [1, 2, 3, 4],
                  "subsample": [0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1],
                  }

    random_search = model_selection.RandomizedSearchCV(model, n_jobs=-2, verbose=10, cv=5,
                                                       param_distributions=parameters, n_iter=1000,
                                                       scoring="f1").fit(x_train, y_train)
    print("Best Model parameters:", random_search.best_params_)
    print("Best Model mean accuracy:", random_search.best_score_)
    return random_search.best_estimator_


def create_model(data_set: pd.DataFrame, train_data: pd.DataFrame, test_data: pd.DataFrame, training: bool = False,
                 make_graphs: bool = False, save_model: bool = False) -> object:
    """ Function to use the dataset and generate a model. It has been set to known good gradient boosting algorithm.

    This function created a known good model if training is set to False, if training is Ture it will call train_model
    to find the best model based on F1 score in short time.
    This function will also write a CSV with the predicted labels appended to the data set. It will also give some
    industry standard machine learning scores.

    :param data_set: entire dataframe of generated training and testing data
    :param train_data: split 70% of the dataset to train the model on
    :param test_data: other 30% of unseen data to test the generated model on
    :param training: boolean to indicate whether to print progress updates
    :param make_graphs: boolean to create graphs for thesis paper
    :param save_model: boolean to indicate to save the generated model for later use
    :return: generated gradient boosting classifier model
    """
    x_train = train_data.drop("label", axis=1).values
    y_train = train_data["label"].values
    x_test = test_data.drop("label", axis=1).values
    y_test = test_data["label"].values
    if training:
        model = train_model(x_train, y_train)
    else:
        model = ensemble.GradientBoostingClassifier(subsample=0.9, n_estimators=3000, min_samples_split=2,
                                                    min_samples_leaf=1, max_features=4, max_depth=10,
                                                    learning_rate=0.3,
                                                    random_state=1)
    model.fit(x_train, y_train)
    predicted_prob = model.predict_proba(x_test)[:, 1]
    predicted = (model.predict_proba(x_test)[:, 1] >= 0.9).astype(bool)
    data_set["label_predicted"] = model.predict(data_set.drop("label", axis=1).values)
    data_set.to_csv("data/chat_labeled_predicted.csv")
    print("predicted data written to data/chat_labeled_predicted.csv")
    recall = metrics.recall_score(y_test, predicted)
    precision = metrics.precision_score(y_test, predicted)
    f1_score = metrics.f1_score(y_test, predicted)
    print("Recall:", round(recall, 2))
    print("Precision:", round(precision, 2))
    print("F1 Score:", round(f1_score, 2))
    print("Detail:")
    print(metrics.classification_report(y_test, predicted, target_names=[str(i) for i in numpy.unique(y_test)]))
    if make_graphs:
        create_model_graphs(model, x_train, y_train, x_test, y_test, predicted, predicted_prob, recall, precision)
    if save_model:
        files = joblib.dump(model, "data/boostinggradient.joblib")
        print("Model is written to:" + str(files))
    return model


def make_prediction(application_ids: list) -> dict:
    """ Function to use the generated model to make recommendations for the given 2 applications

    This function will generate a dataset in a fairly similar way from the OpenAPI documents of the two APIs.
    It will use this dataset and the pre-generated model to make recommendations
    :param application_ids: list of application ids
    :return: a dict containing the connections that recommended
    """
    data = create_data_set(application_ids, training=False)
    try:
        model = joblib.load("data/boostinggradient.joblib")
    except FileNotFoundError:
        data_set, train_data, test_data = read_training_data_set(make_graphs=True)
        model = create_model(data_set, train_data, test_data, make_graphs=True, save_model=True)
    data.drop(
        ["application1_name", "application2_name",
         "application1_path", "application2_path",
         "application1_schema", "application2_schema",
         "application1_description", "application2_description",
         "application1_original_description", "application2_original_description",
         ], axis=1, inplace=True)

    data["label_predicted"] = model.predict_proba(data.drop(
        ["application1_id", "application2_id",
         "application1_endpoint_id", "application2_endpoint_id",
         "application1_original_path", "application2_original_path",
         "application1_operation", "application2_operation",
         "application1_server_override", "application2_server_override",
         ], axis=1).values)[:, 1]
    data = data.loc[data["label_predicted"] >= 0.9]
    return data.to_dict("records")
