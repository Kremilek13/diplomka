import os

import pandas as pd
from ipfn import ipfn

from attributes.code_list import code_list_age_group, code_list_gender, code_list_education
from attributes.marginal_data_reader import age_groups, read_marginal_data
from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import synthetic_population_to_contingency

def read_edu() -> pd.DataFrame:
    data_path = os.path.join(
            os.path.dirname(__file__),
            '../../datasources/individual/education/vzdelani_pohlavi_vek.csv'
    )
    df = pd.read_csv(data_path, sep=",")
    df = df.rename(columns={"vekova_skupina": "age_group", "pohlavi":"gender", "vzdelani":"education", "pocet_obyvatel":"count"})
    code_list_age_group(df)
    code_list_gender(df)
    code_list_education(df)

    print(df)
    return df


def fit_edu(df_synth_pop) -> pd.DataFrame:
    df = read_edu().groupby(['age_group', 'gender', 'education']).sum().reset_index()
    # df["count"] = df["count"].astype(float)

    margins_gender = read_marginal_data(
            ['male', 'female'], 'gender'
    ).groupby(['gender']).sum()["count"]

    margins_age = read_marginal_data(age_groups, 'age_group').groupby('age_group').sum()["count"]

    margins_gender_age = synthetic_population_to_contingency(df_synth_pop, ["gender", "age_group"])["count"]
    margins_age_group = synthetic_population_to_contingency(df_synth_pop, ["age_group"])["count"]
    margins_education = read_df_education_marginal().groupby(
            'education'
    )["count"].sum()

    df_fitted = ipfn.ipfn(
            df.copy().astype({'count': 'float'}),
            aggregates=[margins_gender, margins_age, margins_education, margins_gender_age],
            dimensions=[['gender'], ['age_group'], ['education'], ['gender','age_group']],
            weight_col='count'
    ).iteration()

    name = "education X age group X gender"
    validate_fitted_distribution(df_fitted, margins_age, "age_group", name)
    validate_fitted_distribution(df_fitted, margins_gender, "gender", name)
    validate_fitted_distribution(df_fitted, margins_education, 'education', name)
    validate_fitted_distribution(df_fitted, margins_gender_age, ['gender', 'age_group'], name)


    return df_fitted

def read_df_education_marginal() -> pd.DataFrame:
    df_education_marginal = read_marginal_data(
        ['education_primary_no', 'education_secondary', 'education_higher', 'population'],
        'education'
    ).pivot(
            index="neighb_code", columns='education', values='count'
    )

    unknown = df_education_marginal.population - df_education_marginal.education_primary_no - df_education_marginal.education_secondary - df_education_marginal.education_higher
    df_education_marginal.loc[:, ["education_undefined"]] = unknown

    df_education_marginal = df_education_marginal.drop("population", axis=1).reset_index()

    df_education_marginal = pd.melt(
            df_education_marginal,
            id_vars=["neighb_code"],
            value_vars=["education_primary_no", "education_secondary", "education_higher", "education_undefined"],
            value_name="count",
            var_name="education"
    )

    return df_education_marginal