import os

import pandas as pd
from ipfn import ipfn

from attributes.code_list import code_list_age_group, code_list_gender, code_list_economical_activity
from attributes.marginal_data_reader import age_groups, read_marginal_data
from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import synthetic_population_to_contingency

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


def fit_activity(df_synth_pop) -> pd.DataFrame:
    df = read_activity().groupby(['age_group', 'gender', 'economical_activity']).sum().reset_index()
    df["count"] = df["count"].astype(float)

    margins_gender = read_marginal_data(
            ['male', 'female'], 'gender'
    ).groupby(['gender']).sum()["count"]

    margins_age = read_marginal_data(age_groups, 'age_group').groupby('age_group').sum()["count"]

    margins_gender_age = synthetic_population_to_contingency(df_synth_pop, ["gender", "age_group"])["count"]
    margins_age_group = synthetic_population_to_contingency(df_synth_pop, ["age_group"])["count"]
    margins_education = read_df_activity_marginal().groupby(
            'economical_activity'
    )["count"].sum()

    df_fitted = ipfn.ipfn(
            df.copy().astype({'count': 'float'}),
            aggregates=[margins_gender, margins_age],
            dimensions=[['gender'], ['age_group']],
            weight_col='count'
    ).iteration()

    name = "economical_activity X age group X gender"
    validate_fitted_distribution(df_fitted, margins_age, "age_group", name)
    validate_fitted_distribution(df_fitted, margins_gender, "gender", name)
    validate_fitted_distribution(df_fitted, margins_education, 'economical_activity', name)
    validate_fitted_distribution(df_fitted, margins_gender_age, ['gender', 'age_group'], name)

    return df_fitted

def read_df_activity_marginal() -> pd.DataFrame:
    df_activity_marginal = read_marginal_data(
        ['economical_activity_employed', 'economical_activity_working_retired', 
         'economical_activity_working_student', 'economical_activity_maternity_leave', 'economical_activity_parental_leave',
         'economical_activity_unemployed', 'economical_activity_nonworking_retired', 'economical_activity_selfsufficient',
         'economical_activity_preschool_others_dependent', 'economical_activity_nonworking_students_pupils',
         'economical_activity_undefined'],
        'economical_activity'
    # ).pivot(
    #         index="neighb_code", columns='economical_activity', values='count'
    )

    # children = df_activity_marginal.population - df_activity_marginal.economical_activity_employed - df_activity_marginal.economical_activity_working_retired - df_activity_marginal.economical_activity_working_student - df_activity_marginal.economical_activity_selfsufficient - df_activity_marginal.economical_activity_unemployed - df_activity_marginal.economical_activity_nonworking_retired - df_activity_marginal.economical_activity_parental_leave - df_activity_marginal.economical_activity_preschool_others_dependent - df_activity_marginal.economical_activity_undefined
    # df_activity_marginal['economical_activity_employed'] = df_activity_marginal['economical_activity_employed'] + children
    # # df_education_marginal.loc[:, ["education_primary_no"]] = children

    # df_education_marginal = df_education_marginal.drop("population", axis=1).reset_index()

    # df_education_marginal = pd.melt(
    #         df_education_marginal,
    #         id_vars=["neighb_code"],
    #         value_vars=["education_primary_no", "education_secondary", "education_higher", "education_undefined"],
    #         value_name="count",
    #         var_name="education"
    # )

    return df_activity_marginal