import os.path

import numpy as np
import pandas as pd
from ipfn import ipfn

from attributes.marginal_data_reader import read_marginal_data
from data_tools.dynamic_mappers import cbs_age_group_rename_transform
from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import synthetic_population_to_contingency


def read_df_migration_background_joint() -> pd.DataFrame:
    """
    Migration background was downloaded formatted  as follows:
        https://opendata.cbs.nl/#/CBS/nl/dataset/84910NED/table?dl=9D32C
        (Download -> CSV zonder statistische symbolen)

    Filters:
        Region: 's Gravenhage (gemeente) (Hague)
        Generatie: Totaal
        Perioden: 2019
    Column Variables:
        Onderwerp -> Bevolking op 1 januari
    Row Variables:
        Leeftijd (all except "Total")
        Geslacht ("Mannen" and "Vrouwen")
        Migratieachtergrond:
            - Nederlandse achtergrond
            - Westerse migratieachtergrond
            - Niet-westerse migratieachtergrond

    Pohlaví, věková skupina, počet
    
    Returns:

    """
    data_file = os.path.join(
            os.path.dirname(__file__),
            '../../datasources/individual/migration_background'
            '/Bev__migratieachtergr__regio__2010_2022_29122023_115517.csv'
    )
    df_migration_joint = pd.read_csv(data_file, sep=";")[
        ["Geslacht", "Leeftijd", "Migratieachtergrond", "Bevolking op 1 januari (aantal)"]]

    df_migration_joint.rename(
            columns=dict(
                    zip(df_migration_joint.columns, ["gender", "small_age_group", "migration_background", "count"])),
            inplace=True)

    df_migration_joint.replace({
        "Mannen": "male",
        "Vrouwen": "female",
        "Nederlandse achtergrond": "Dutch",
        "Westerse migratieachtergrond": "Western",
        "Niet-westerse migratieachtergrond": "NonWestern"
    }, inplace=True)

    df_migration_joint["small_age_group"] = df_migration_joint.small_age_group.transform(cbs_age_group_rename_transform)

    return df_migration_joint


def read_df_migration_background_marginal() -> pd.DataFrame:
    df_migration_marginal = read_marginal_data(
            ["Western", "NonWestern", "population"],
            "migration_background"
    ).pivot(
            index="neighb_code", columns='migration_background', values='count'
    )

    dutch = df_migration_marginal.population - df_migration_marginal.Western - df_migration_marginal.NonWestern
    df_migration_marginal.loc[:, ["Dutch"]] = dutch

    df_migration_marginal = df_migration_marginal.drop("population", axis=1).reset_index()

    df_migration_marginal = pd.melt(
            df_migration_marginal,
            id_vars=["neighb_code"],
            value_vars=["Dutch", "Western", "NonWestern"],
            value_name="count",
            var_name="migration_background"
    )

    return df_migration_marginal


def add_small_age_group(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    for redundant_col in ["level_0", "index"]:
        if redundant_col in df_synth_pop.columns:
            df_synth_pop = df_synth_pop.drop(redundant_col, axis=1)
    df_synth_pop["small_age_group"] = None
    df_synth_pop.astype({"small_age_group": 'object'})
    df_synth_pop.loc[df_synth_pop.age >= 90, "small_age_group"] = "90+"
    df_synth_pop.loc[df_synth_pop.age < 90, "small_age_group"] = df_synth_pop[df_synth_pop.age < 90].age.transform(
            lambda x: "{lower}-{upper}".format(lower=int(np.floor(x / 5) * 5), upper=int(np.floor(x / 5) * 5) + 4)
    )
    return df_synth_pop


def fit_df_migration_background(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    """

    Args:
        df_synth_pop:

    Returns:

    """
    df_migration_joint = read_df_migration_background_joint()

    margins_gender = read_marginal_data(['male', 'female'], 'gender').groupby(['gender']).sum()["count"]
    margins_age_group = synthetic_population_to_contingency(df_synth_pop, ["small_age_group"])["count"]
    margins_gender_age = synthetic_population_to_contingency(df_synth_pop, ["gender", "small_age_group"])["count"]
    margins_migration_background = read_df_migration_background_marginal().groupby(
            'migration_background'
    )["count"].sum()

    df_fitted = ipfn.ipfn(
            df_migration_joint.copy().astype({'count': 'float'}),
            aggregates=[margins_gender, margins_age_group, margins_migration_background, margins_gender_age],
            dimensions=[['gender'], ['small_age_group'], ['migration_background'], ['gender', 'small_age_group']],
            weight_col='count'
    ).iteration()

    name = "migration background X gender X age group"
    validate_fitted_distribution(df_fitted, margins_gender, 'gender', name)
    validate_fitted_distribution(df_fitted, margins_age_group, 'small_age_group', name)
    validate_fitted_distribution(df_fitted, margins_migration_background, 'migration_background', name)
    validate_fitted_distribution(df_fitted, margins_gender_age, ['gender', 'small_age_group'], name)

    return df_fitted
