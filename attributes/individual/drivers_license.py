import os
import re

import numpy as np
import pandas as pd
from ipfn import ipfn

from attributes.marginal_data_reader import read_province_population_size
from gensynthpop.utils.extractors import synthetic_population_to_contingency


def read_joint_driver_license() -> pd.DataFrame:
    """
    Driver License data was downloaded formatted as follows:
        https://opendata.cbs.nl/#/CBS/nl/dataset/83488NED/table?dl=A628D
        (Download -> CSV zonder statistische symbolen)

    Filters:
        Region: Zuid Holland (PV)
        Perioden: 2019
        Onderwerp: Personen met Rijbewijs
    Column Variables:
        Rijbewijscategorie:
            Autorijbewijs totaal, Bromfietsrijbewijs, Motorrijbewijs
    Row Variables:
        Leeftijd (all except "Totaal" and "Leeftijd onbekend")

    Věková skupina počet

    Returns:

    """
    data_path = os.path.join(
            os.path.dirname(__file__),
            "../../datasources/individual/drivers_license/Personen_met_rijbewijs__categorie__regio_19052024_184228.csv"
    )

    df = pd.read_csv(data_path, sep=";")[
        ["Leeftijd rijbewijshouder", "Rijbewijscategorie", "Personen met rijbewijs (aantal)"]
    ].rename(columns={
        "Leeftijd rijbewijshouder": 'license_age',
        "Rijbewijscategorie": 'license',
        "Personen met rijbewijs (aantal)": 'count'
    })

    assert df.groupby('license_age').sum().loc['Totaal']["count"] == \
           df.groupby('license_age').sum()[df.groupby('license_age').sum().index != 'Totaal'][
               "count"].sum(), "CBS data totals do not match data"
    df = df.pivot(index='license_age', columns='license', values='count')
    df.index = df.index.map(
            lambda i: '75+' if i == '75 jaar of ouder' else re.sub(r'(\d+) tot (\d+) jaar', r'\1-\2', i))
    return df[df.index != 'Totaal']


def add_license_age_to_synthetic_population(df_synth_pop: pd.DataFrame):
    df_synth_pop.loc[:, 'license_age'] = None
    age_groups = read_joint_driver_license().reset_index().license_age.unique()
    df_synth_pop.loc[df_synth_pop.age == 15, 'license_age'] = '15'
    for age_group in list(age_groups) + ['0-15']:
        if "-" in age_group:
            start, end = map(int, age_group.split("-"))
            # for i in range(start, end):
            df_synth_pop.loc[df_synth_pop.age.isin(range(start, end)), 'license_age'] = age_group

    df_synth_pop.loc[df_synth_pop.age.isin(range(75, 101)), 'license_age'] = '75+'

    assert sum(df_synth_pop.license_age.isna()) == 0, "License age not assigned to all agents"

    return df_synth_pop


def add_totals_to_driver_license(df_licenses: pd.DataFrame, df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    """
    Add the known population counts for the region to the driver's licence data frame, using the relative frequencies
    of the integer ages already added to the synthetic population

    Args:
        df_licenses:
        df_synth_pop:

    Returns:

    """
    df_synt_age_distribution = synthetic_population_to_contingency(df_synth_pop, ['age'])
    totals = read_province_population_size()

    df_licenses.loc[:, 'total'] = np.nan
    df_licenses.loc['0-15', 'total'] = totals[totals.index.isin(['<5', '5-10', '10-15'])]['count'].sum()

    df_licenses.loc['15', 'total'] = get_relative_subgroup_size(df_synt_age_distribution, totals, 15, 16, 15, 20)
    df_licenses.loc['16-18', 'total'] = get_relative_subgroup_size(df_synt_age_distribution, totals, 16, 18, 15, 20)
    df_licenses.loc['18-20', 'total'] = get_relative_subgroup_size(df_synt_age_distribution, totals, 18, 20, 15, 20)
    df_licenses.loc['20-25', 'total'] = totals.loc['20-25']['count']
    df_licenses.loc['25-30', 'total'] = get_relative_subgroup_size(df_synt_age_distribution, totals, 25, 30, 25, 45)
    df_licenses.loc['30-40', 'total'] = get_relative_subgroup_size(df_synt_age_distribution, totals, 30, 40, 25, 45)
    df_licenses.loc['40-50', 'total'] = (get_relative_subgroup_size(df_synt_age_distribution, totals, 40, 45, 25, 45) +
                                         get_relative_subgroup_size(df_synt_age_distribution, totals, 45, 50, 45, 65))
    df_licenses.loc['50-60', 'total'] = get_relative_subgroup_size(df_synt_age_distribution, totals, 50, 60, 45, 65)
    df_licenses.loc['60-65', 'total'] = get_relative_subgroup_size(df_synt_age_distribution, totals, 60, 65, 45, 65)
    df_licenses.loc['65-70', 'total'] = get_relative_subgroup_size(df_synt_age_distribution, totals, 65, 70, 65, 80)
    df_licenses.loc['70-75', 'total'] = get_relative_subgroup_size(df_synt_age_distribution, totals, 70, 75, 65, 80)
    df_licenses.loc['75+', 'total'] = get_relative_subgroup_size(df_synt_age_distribution, totals, 75, 80, 65, 80) + \
                                      totals.loc['80+']['count']

    assert "totals", totals['count'].sum() == df_licenses['total'].sum()

    return df_licenses


def get_relative_subgroup_size(df: pd.DataFrame, population_totals: pd.DataFrame, subgroup_start: int,
                               subgroup_end: int, ingroup_start: int, ingroup_end: int):
    rel_size = df.loc[subgroup_start:subgroup_end - 1]['count'].sum() / df.loc[ingroup_start:ingroup_end - 1][
        'count'].sum()
    return rel_size * population_totals.loc[f'{ingroup_start}-{ingroup_end}']['count']


def get_car_driver_license(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    df = read_joint_driver_license().rename(columns={'Autorijbewijs totaal': 'yes'})
    df = add_totals_to_driver_license(df, df_synth_pop)[['yes', 'total']].fillna(0.)
    df.loc[:, 'no'] = df.total - df.yes
    df = df.drop('total', axis=1)
    df = df.reset_index().melt(id_vars='license_age', value_vars=['yes', 'no'], var_name='car_license',
                               value_name='count')
    return df


def fit_car_driver_license(df_car_driver_license: pd.DataFrame, df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    return ipfn.ipfn(
            df_car_driver_license,
            [synthetic_population_to_contingency(df_synth_pop, ["license_age"], False)["count"]],
            [['license_age']],
            'count'
    ).iteration()


def get_and_fit_car_driver_license(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    df = get_car_driver_license(df_synth_pop)
    return fit_car_driver_license(df, df_synth_pop)


def get_and_fit_motor_cycle_license(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    df = read_joint_driver_license().rename(columns={'Motorrijbewijs': 'yes'})
    df = add_totals_to_driver_license(df, df_synth_pop)[['yes', 'total']].fillna(0.)
    df.loc[:, 'no'] = df.total - df.yes
    df = df.drop('total', axis=1)
    df = df.reset_index().melt(id_vars='license_age', value_vars=['yes', 'no'], var_name='motorcycle_license',
                               value_name='count')
    return ipfn.ipfn(
            df,
            [synthetic_population_to_contingency(df_synth_pop, ["license_age"], False)["count"]],
            [['license_age']],
            'count'
    ).iteration()


def get_and_fit_conditional_moped_license(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    """
    In the Netherlands, the Moped License is automatically granted to car drivers.
    The number of moped licenses is higher than the number of car licenses in each age category, which suggests the
    moped license numbers include those granted through a car license.
    For this reason, a conditional data set is required.

    Returns:
    """
    # Read moped license counts and add region totals
    df_moped = read_joint_driver_license().rename(
            columns={'Bromfietsrijbewijs': 'moped', 'Autorijbewijs totaal': 'car'})
    df_moped = add_totals_to_driver_license(df_moped, df_synth_pop)[["car", "moped", "total"]].fillna(0.)

    # Join over the car license data frame, because each car driver has a moped license
    df_car = get_car_driver_license(df_synth_pop).set_index('license_age')
    df = df_car.join(df_moped, how='left').reset_index()

    # Everyone with a car license has moped license, which means that the remaining moped licenses go to
    # (moped - car) number of individuals without car license. To make up the total, (total - moped) has neither a car
    # nor a moped license
    msk_car = df.car_license == 'yes'
    df.loc[msk_car, 'no_moped'] = 0.
    df.loc[msk_car, 'yes_moped'] = df.loc[msk_car, 'car']
    df.loc[~msk_car, 'yes_moped'] = df.loc[~msk_car, 'moped'] - df.loc[~msk_car, 'car']
    df.loc[~msk_car, 'no_moped'] = df.loc[~msk_car, 'total'] - df.loc[~msk_car, 'moped']

    # Melt to get a nice frame of moped license conditioned over age and car license
    df_joint_moped = df[["license_age", "car_license", "yes_moped", "no_moped"]].rename(
            columns=dict(yes_moped='yes', no_moped='no'))
    df_joint_moped = df_joint_moped.melt(id_vars=['license_age', 'car_license'], value_vars=['yes', 'no'],
                                         var_name='moped_license', value_name='count')

    assert df_joint_moped.loc[
               df_joint_moped.moped_license == 'yes', 'count'].sum() == read_joint_driver_license(

    ).Bromfietsrijbewijs.sum()
    assert df_moped.total.sum() == df_joint_moped['count'].sum()

    df_joint_moped_fitted = ipfn.ipfn(
            df_joint_moped,
            [
                synthetic_population_to_contingency(df_synth_pop, ["license_age"], False)["count"],
                synthetic_population_to_contingency(df_synth_pop, ["car_license"], False)["count"],
                synthetic_population_to_contingency(df_synth_pop, ["license_age", "car_license"], True)["count"]
            ],
            [['license_age'], ['car_license'], ['license_age', 'car_license']],
            'count'
    ).iteration()

    return df_joint_moped_fitted
