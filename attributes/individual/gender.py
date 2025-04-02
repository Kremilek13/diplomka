import os

import pandas as pd
from ipfn import ipfn

from attributes.marginal_data_reader import age_groups, read_marginal_data
from gensynthpop.evaluation.validation import validate_fitted_distribution


def _read_joint_age_gender() -> pd.DataFrame:
    """
    Reads the joint distribution of gender and age group.

    To give the existing synthetic population a chance, we will use the formatted data prepared in R for this region,
    instead of going back to the source entirely.

    = age (věk), male (počet mužů), female (počet žen), total (počet mužů + počet žen), age_group (definované věkové skupiny), group_propensity (podíl total / celkový počet lidí ve věkové skupině)
    celé je to za region (Hague)

    Věk, věková skupina, pohlaví

    Returns:

    """
    data_path = os.path.join(
            os.path.dirname(__file__),
            '../../datasources/individual/gender/gender_age-03759NED-formatted.csv'
    )
    df = pd.read_csv(data_path)
    df = pd.melt(df, id_vars=["age_group"], value_vars=["male", "female"], var_name="gender", value_name="count")
    df.age_group = df.age_group.transform(
            lambda x: "65+" if x == "age_over65" else x.replace("age_", "").replace("_", "-")
    )
    df = df.groupby(['age_group', 'gender']).sum()

    return df


def fit_joint_age_gender() -> pd.DataFrame:
    """
    Updates the joint distribution of age and gender to fit various margins before we start using it to
    add gender to a synthetic population

    Returns:

    """
    df = _read_joint_age_gender().reset_index()
    df["count"] = df["count"].astype(float)

    margins_gender = read_marginal_data(
            ['male', 'female'], 'gender'
    ).groupby(['gender']).sum()["count"]

    margins_age = read_marginal_data(age_groups, 'age_group').groupby('age_group').sum()["count"]

    df_fitted = ipfn.ipfn(
            df.copy(),
            aggregates=[margins_gender, margins_age],
            dimensions=[['gender'], ['age_group']],
            weight_col='count'
    ).iteration()

    validate_fitted_distribution(df_fitted, margins_age, "age_group", "age X gender")
    validate_fitted_distribution(df_fitted, margins_gender, "gender", "age X gender")

    return df_fitted
