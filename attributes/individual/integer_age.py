import os.path

import pandas as pd
from ipfn import ipfn

from attributes.marginal_data_reader import age_groups, read_marginal_data
from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import age_to_age_group


def read_df_integer_age() -> pd.DataFrame:
    '''
    Zde jsou použitá data za celé Nizozemí

    Pohlaví, věk, počet
    na řádku 24 - nutné opravit věk
    '''

    data_file = os.path.join(
            os.path.dirname(__file__),
            '../../datasources/individual/integer_age/Leeftijdsopbouw Nederland 2019.csv',
    )
    df_integer_age = pd.read_csv(data_file, sep=";")
    df_integer_age.loc[0, "Leeftijd"] = "105 jaar"
    df_integer_age["Leeftijd"] = df_integer_age.Leeftijd.transform(lambda x: int(x.replace(" jaar", "")))
    df_integer_age.rename(columns={"Mannen": "male", "Vrouwen": "female", "Leeftijd": "age"}, inplace=True)
    df_integer_age["male"] = df_integer_age.male.transform(lambda x: int(x.replace(" ", "")))
    df_integer_age["female"] = df_integer_age.female.transform(lambda x: int(x.replace(" ", "")))
    df_integer_age = df_integer_age.melt(id_vars="age", value_vars=["male", "female"], var_name="gender",
                                         value_name="count")
    df_integer_age["age_group"] = df_integer_age.age.transform(lambda age: age_to_age_group(age, age_groups))
    df_integer_age = df_integer_age[["age_group", "gender", "age", "count"]]
    return df_integer_age


def fit_df_integer_age() -> pd.DataFrame:
    df = read_df_integer_age()
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

    name = "integer age X age group X gender"
    validate_fitted_distribution(df_fitted, margins_age, "age_group", name)
    validate_fitted_distribution(df_fitted, margins_gender, "gender", name)

    return df_fitted
