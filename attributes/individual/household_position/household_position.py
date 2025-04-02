import os

import pandas as pd
from ipfn import ipfn

from attributes.marginal_data_reader import read_marginal_data
from data_tools.dynamic_mappers import cbs_age_group_rename_transform
from data_tools.static_mappings import household_data_code_map
from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import synthetic_population_to_contingency


def get_household_position_joint_age_gender() -> pd.DataFrame():
    df = read_household_data('gender', 'age_group', 'child', 'single', 'non_married_no_children',
                             'married_no_children', 'non_married_with_children', 'married_with_children',
                             'single_parent')
    df = pd.melt(df, id_vars=["gender", "age_group"],
                 value_vars=['child', 'single', 'non_married_no_children', 'married_no_children',
                             'non_married_with_children', 'married_with_children', 'single_parent'],
                 var_name='household_position', value_name="count")

    return df


def read_household_data(*columns: str) -> pd.DataFrame:
    """
    Household data was formatted as follows:
        https://opendata.cbs.nl/#/CBS/nl/dataset/71488ned/table?dl=9D241
        (Download -> CSV zonder statistische symbolen)

    Filters:
        Region: 's Gravenhage (gemeente)
        Perioden: 2019
    Column Variables:
        Onderwerpen: All selected
    Row Variables:
        Leeftijd (all, except "total")
        Geslacht (all, except "total")
    Args:
        *columns:

    Returns:

    """
    data_path = os.path.join(
            os.path.dirname(__file__),
            "../../../datasources/individual/household_position/Huishoudens__personen__regio_26122023_151215.csv"
    )

    df = pd.read_csv(data_path, sep=";")

    df.rename(columns=household_data_code_map, inplace=True)
    df.age_group = df.age_group.transform(cbs_age_group_rename_transform)
    df.replace({"Mannen": "male", "Vrouwen": "female"}, inplace=True)
    df.drop(["region", "period"], axis=1, inplace=True)
    df.fillna(0, inplace=True)
    df = df.astype(int, errors='ignore')
    if len(columns) > 0:
        return df[list(columns)]
    else:
        return df


def read_local_household_composition() -> pd.DataFrame:
    """
    https://opendata.cbs.nl/#/CBS/nl/dataset/71486ned/table?dl=A68AA

    Regio's: 's-Gravenhage (gemeente)
    Perioden: 2019

    Row Variables:
        - Leeftijd referentiepersoon (all except total)

    Column Variables:
        Particuliere huishoudens: samenstelling
            - Eenpersoonshuishouden
            - Meerpersoonshuishouden
                - Meerpersoonshuishoudens zonder kinderen
                - Meerpersoonshuishoudens met kinderen
                - Niet-gehuwd paar
                    - 0 kinderen
                    - 1 kind
                    - 2 kinderen
                    - 3 of meer kinderen
                - Gehuwd paar
                    - 0 kinderen
                    - 1 kind
                    - 2 kinderen
                    - 3 of meer kinderen
                - Eenouderhuishouden
                    - 1 kind
                    - 2 kinderen
                    - 3 of meer kinderen
                - Overig huishouden
    Returns:

    """
    data_path = os.path.join(
            os.path.dirname(__file__),
            "../../../datasources/individual/household_position/Huishoudens__samenstelling__regio_25052024_174751.csv"
    )
    df = pd.read_csv(data_path, sep=';').drop(['Perioden', "Regio's"], axis=1)
    df.rename(columns={
        'Leeftijd referentiepersoon': 'reference_person_age',
        'Particuliere huishoudens: samenstelling/Eenpersoonshuishouden (aantal)': 'single',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Meerpersoonshuishoudens zonder kinderen ('
        'aantal)': 'no_children',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Meerpersoonshuishoudens met kinderen ('
        'aantal)': 'has_children',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Niet-gehuwd paar/0 kinderen (aantal)':
            'non_married_0_children',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Niet-gehuwd paar/1 kind (aantal)':
            'non_married_1_children',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Niet-gehuwd paar/2 kinderen (aantal)':
            'non_married_2_children',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Niet-gehuwd paar/3 of meer kinderen ('
        'aantal)': 'non_married_3_children',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Gehuwd paar/0 kinderen (aantal)':
            'married_0_children',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Gehuwd paar/1 kind (aantal)':
            'married_1_children',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Gehuwd paar/2 kinderen (aantal)':
            'married_2_children',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Gehuwd paar/3 of meer kinderen (aantal)':
            'married_3_children',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Eenouderhuishouden/1 kind (aantal)':
            'single_parent_1_children',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Eenouderhuishouden/2 kinderen (aantal)':
            'single_parent_2_children',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Eenouderhuishouden/3 of meer kinderen ('
        'aantal)': 'single_parent_3_children',
        'Particuliere huishoudens: samenstelling/Meerpersoonshuishouden/Overig huishouden (aantal)': 'miscellaneous',
    }, inplace=True)
    for i in range(4):
        df.loc[:, f'couple_{i}_children'] = df[f'married_{i}_children'] + df[f'non_married_{i}_children']
        df.drop([f'married_{i}_children', f'non_married_{i}_children'], axis=1, inplace=True)

    return df


def read_households_margins():
    df_households = read_marginal_data(
            ['population', 'single_person', 'without_children', 'with_children'],
            'households')
    df_households = df_households.pivot(index='neighb_code', columns='households', values='count')
    df_households.loc[:, 'in_hh_without_children'] = df_households.without_children * 2
    df_households.loc[:,
    'in_hh_with_children'] = (df_households.population - df_households.single_person -
                              df_households.in_hh_without_children)
    df_households = df_households[["single_person", "in_hh_with_children", "in_hh_without_children"]]

    df_households = df_households.reset_index().melt(id_vars=['neighb_code'],
                                                     value_vars=["single_person", "in_hh_with_children",
                                                                 "in_hh_without_children"],
                                                     var_name='household_type', value_name='count')

    return df_households


def fit_household_position_joint_age_gender(df_synth_pop: pd.DataFrame) -> pd.DataFrame():
    df = pd.read_pickle(os.path.join(
            os.path.dirname(__file__), 'processed/df_households_with_position_and_children.pkl'))
    df = df.rename(columns={"age_group": "small_age_group"}).astype({"count": float})
    margins_gender = read_marginal_data(['male', 'female'], 'gender').groupby('gender')['count'].sum()
    margins_age_group_gender = synthetic_population_to_contingency(df_synth_pop, ["gender", "small_age_group"], True)
    margins_age_group = margins_age_group_gender.reset_index().groupby("small_age_group")["count"].sum()
    margins_age_group_gender = margins_age_group_gender["count"]
    margins_households = read_households_margins().groupby('household_type')['count'].sum()

    df_fitted = ipfn.ipfn(
            df.copy(),
            aggregates=[
                margins_gender,
                margins_age_group,
                margins_age_group_gender,
                margins_households
            ],
            dimensions=[
                ['gender'], ['small_age_group'], ['gender', 'small_age_group'], ['household_type']],
            weight_col='count'
    ).iteration()

    name = "relationship_status X gender X age group"
    validate_fitted_distribution(df_fitted, margins_gender, 'gender', name)
    validate_fitted_distribution(df_fitted, margins_age_group, 'small_age_group', name)
    validate_fitted_distribution(df_fitted, margins_age_group_gender, ['gender', 'small_age_group'], name)
    validate_fitted_distribution(df_fitted, margins_households, ['household_type'], name)

    return df_fitted
