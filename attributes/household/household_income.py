import os
import re

import pandas as pd
from ipfn import ipfn

from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import synthetic_population_to_contingency


def add_household_type_and_income_age_group(df_synth_households: pd.DataFrame) -> pd.DataFrame:
    df_synth_households.loc[:, 'income_age_group'] = df_synth_households.main_bread_winner_age.map(
            lambda age: '<25' if age < 25 else '65+' if age >= 65 else '25-45' if 25 < age <= 45 else '45-65')

    couple_with_children = ['married_with_1_children',
                            'married_with_2_children', 'married_with_3_children',
                            'non_married_with_1_children',
                            'non_married_with_2_children', 'non_married_with_3_children',
                            ]
    single_parent = ['single_parent_1_children', 'single_parent_2_children',
                     'single_parent_3_children']
    couple_no_children = ['married_no_children', 'non_married_no_children', ]

    df_synth_households.loc[:, 'income_household_type'] = df_synth_households.hh_type.map(
            {hht: 'couple_with_children' for hht in couple_with_children} | {
                hht: 'single_parent' for hht in single_parent} | {
                hht: 'couple_no_children' for hht in couple_no_children} | {'single': 'single'}
    )

    return df_synth_households


def read_household_income():
    """
    https://opendata.cbs.nl/#/CBS/nl/dataset/85064NED/table?dl=A68B8

    Populatie: Particuliere huishoudens incl. studenten
    Regio's: 'S-Gravenhage (gemeente)
    Perioden: 2019

    Row Variables:
        - Particuliere huishoudens
        - Inkomen
            - Gemiddeld gestandaardiseerd inkomen
            - Mediaan gestandaardiseerd inkomen
            - Gemiddeld besteedbaar inkomen
            - Mediaan besteedbaar inkomen
        - Verdeling inkomen
            - Gestandaardiseerd inkomen: 1e 10%-groep
            - Gestandaardiseerd inkomen: 2e 10%-groep
            - Gestandaardiseerd inkomen: 3e 10%-groep
            - Gestandaardiseerd inkomen: 4e 10%-groep
            - Gestandaardiseerd inkomen: 5e 10%-groep
            - Gestandaardiseerd inkomen: 6e 10%-groep
            - Gestandaardiseerd inkomen: 7e 10%-groep
            - Gestandaardiseerd inkomen: 8e 10%-groep
            - Gestandaardiseerd inkomen: 9e 10%-groep
            - Gestandaardiseerd inkomen: 10e 10%-groep
    Column Variables:
        - Kenmerken
            - Samenstelling huishouden
                - Type: Eenpersoonshuishouden
                - Type: Meerpersoonshuishouden
                - Type: Eenoudergezin
                - Type: Paar, zonder kind
                - Type: Paar, met kind(eren)
                - Type: Meerpersoonshuishouden, overig
            - Hoofdkostwinner Leeftijd:
                - Hoofdkostwinner: tot 25 jaar
                - Hoofdkostwinner: 25 tot 45 jaar
                - Hoofdkostwinner: 45 tot 65 jaar
                - Hoofdkostwinner: 65 jaar of ouder
            - Hoofdkostwinner: migratieachtergrond
                - Hoofdkostwinner: Nederland
                - Hoofdkostwinner: westers
                - Hoofdkostwinner: niet-westers

    Returns:

    """
    data_path = os.path.join(
            os.path.dirname(__file__),
            "../../datasources/household/household_income/Inkomen_huishoudens__kenmerken__regio_25052024_182249.csv"
    )
    df = pd.read_csv(data_path, sep=';')
    df.drop(['Populatie', "Regio's", 'Perioden', 'Particuliere huishoudens (x 1 000)'], axis=1, inplace=True)

    df.rename(
            columns=lambda x: re.sub(r'Verdeling inkomen/Gestandaardiseerd inkomen: (\d+)e 10%-groep \(%\)', r'\1', x),
            inplace=True)
    df.rename(
            columns=lambda x: re.sub(r'Inkomen/(\w+) (\w+) inkomen \(1 000 euro\)', r'\1-\2', x), inplace=True)

    # Translate terminology
    df.replace(({
        'Type: Eenpersoonshuishouden': 'single',
        'Type: Eenoudergezin': 'single_parent',
        'Type: Paar, zonder kind': 'couple_no_children',
        'Type: Paar, met kind(eren)': 'couple_with_children',
        'Hoofdkostwinner: tot 25 jaar': '<25',
        'Hoofdkostwinner: 25 tot 45 jaar': '25-45',
        'Hoofdkostwinner: 45 tot 65 jaar': '45-65',
        'Hoofdkostwinner: 65 jaar of ouder': '65+',
        'Hoofdkostwinner: Nederland': 'Dutch',
        'Hoofdkostwinner: westers': 'Western',
        'Hoofdkostwinner: niet-westers': 'NonWestern',
    }), inplace=True)

    # These two household types subsume some of the others
    df = df[
        ~df['Kenmerken van huishoudens'].isin(['Type: Meerpersoonshuishouden', 'Type: Meerpersoonshuishouden, overig'])]

    # Trick: The margins are provided by three different categories. Can we make an estimate of the joint distribution
    # from nothing else?
    income_groups = list(map(str, range(1, 11)))

    df_margins_hh_type = df[
        df['Kenmerken van huishoudens'].isin(
                ['single', 'single_parent', 'couple_no_children', 'couple_with_children'])].set_index(
            'Kenmerken van huishoudens')[list(map(str, range(1, 11)))]
    df_margins_hh_type.index.name = "hh_type"

    df_margins_age = df[df['Kenmerken van huishoudens'].isin(['<25', '25-45', '45-65', '65+'])].set_index(
            'Kenmerken van huishoudens')[list(map(str, range(1, 11)))]
    df_margins_age.index.name = "age_group"

    df_margins_migration = df[df['Kenmerken van huishoudens'].isin(['Dutch', 'Western', 'NonWestern'])].set_index(
            'Kenmerken van huishoudens')[list(map(str, range(1, 11)))]
    df_margins_migration.index.name = "migration_background"

    df_joint = df_margins_hh_type.index.to_frame().merge(df_margins_age.index.to_series(), how='cross').merge(
            df_margins_migration.index.to_series(), how='cross').merge(
            df_margins_hh_type.melt(value_vars=map(str, range(1, 11)), var_name='income_group', value_name='count',
                                    ignore_index=False), how='left',
            left_on='hh_type', right_index=True).reset_index(drop=True)
    df_joint = df_joint.astype({'count': float})

    df_joint = ipfn.ipfn(
            df_joint,
            [
                df_margins_hh_type.sum(axis=1),
                df_margins_hh_type.melt(
                        value_vars=list(map(str, range(1, 11))), var_name='income_group', value_name='count',
                        ignore_index=False
                ).reset_index().set_index(
                        ['hh_type', 'income_group'])['count'],
                df_margins_age.sum(axis=1),
                df_margins_age.melt(
                        value_vars=list(map(str, range(1, 11))), var_name='income_group', value_name='count',
                        ignore_index=False
                ).reset_index().set_index(
                        ['age_group', 'income_group'])['count'],
                df_margins_migration.sum(axis=1),
                df_margins_migration.melt(
                        value_vars=list(map(str, range(1, 11))), var_name='income_group', value_name='count',
                        ignore_index=False
                ).reset_index().set_index(
                        ['migration_background', 'income_group'])['count']
            ],
            [
                ['hh_type'],
                ["hh_type", "income_group"],
                ['age_group'],
                ['age_group', 'income_group'],
                ['migration_background'],
                ['migration_background', 'income_group']
            ],
            'count'
    ).iteration()

    return df_joint


def fit_joint_household_income(df_synth_households: pd.DataFrame) -> pd.DataFrame:
    margins = [
        synthetic_population_to_contingency(df_synth_households, dm, len(dm) > 1)['count']
        for dm in hh_income_margin_names]

    df_joint = read_household_income().rename(columns={
        'age_group': 'income_age_group',
        'hh_type': 'income_household_type',
        'migration_background': 'main_bread_winner_migration_background'
    })

    df_fitted = ipfn.ipfn(
            df_joint,
            margins,
            hh_income_margin_names,
            'count'
    ).iteration()

    for dm, margin in zip(hh_income_margin_names, margins):
        validate_fitted_distribution(
                df_fitted, margin, dm, 'household income group'
        )

    return df_fitted


hh_income_margin_names = [
    ['income_age_group'],
    ['income_household_type'],
    ['main_bread_winner_migration_background'],
    ['income_age_group', 'income_household_type'],
    ['income_age_group', 'main_bread_winner_migration_background'],
    ['income_household_type', 'main_bread_winner_migration_background'],
    ['income_age_group', 'main_bread_winner_migration_background', 'income_household_type']
]
