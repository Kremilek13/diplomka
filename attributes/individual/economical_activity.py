import os

import pandas as pd
from ipfn import ipfn

from attributes.code_list import code_list_age_group, code_list_gender, code_list_economical_activity
from attributes.marginal_data_reader import age_groups, read_marginal_data
from gensynthpop.evaluation.validation import validate_fitted_distribution

def read_activity() -> pd.DataFrame:
    data_path = os.path.join(
            os.path.dirname(__file__),
            '../../datasources/individual/economical_activity/EA_pohlavi_vek.csv'
    )
    df = pd.read_csv(data_path, sep=",")
    df = df.rename(columns={"vekova_skupina": "age_group", "pohlavi":"gender", "ekonomicka_aktivita":"economical_activity", "pocet_obyvatel":"count"})
    code_list_age_group(df)
    code_list_gender(df)
    code_list_economical_activity(df)

    print(df)
    return df


def fit_activity() -> pd.DataFrame:
    df = read_activity()
    df["count"] = df["count"].astype(float)

    margins_gender = read_marginal_data(
            ['male', 'female'], 'gender'
    ).groupby(['gender']).sum()["count"]

    margins_age = read_marginal_data(age_groups, 'age_group').groupby('age_group').sum()["count"]

    df_fitted = ipfn.ipfn(
            df.copy().astype({'count': 'float'}),
            aggregates=[margins_gender, margins_age],
            dimensions=[['gender'], ['age_group']],
            weight_col='count'
    ).iteration()

    name = "education X age group X gender"
    validate_fitted_distribution(df_fitted, margins_age, "age_group", name)
    validate_fitted_distribution(df_fitted, margins_gender, "gender", name)

    return df_fitted