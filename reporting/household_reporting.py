from typing import List

import pandas as pd

from attributes.household.household_income import fit_joint_household_income, hh_income_margin_names
from attributes.household.post_code import read_pc6_data
from attributes.household.vehicle_ownership import fit_vehicle_ownership_for_type, get_vehicle_ownership_dimensions
from attributes.marginal_data_reader import read_marginal_data
from gensynthpop.evaluation.reporting import ComparisonTuple, create_score_table
from gensynthpop.utils.extractors import synthetic_population_to_contingency
from reporting.reporting import readable_name, score_table_household_position


def create_household_score_table(df_synth_pop: pd.DataFrame, df_synth_households: pd.DataFrame):
    population_rows = [
        score_table_household_position
    ]

    create_score_table(df_synth_pop, population_rows,
                       'output/scores/latex/synthpop_dhwz_population_after_households_results_table.tex', True, True)

    household_rows = [
        score_3_type_households,
        score_postal_code,
        score_income_group,
        score_car_ownership,
        score_motor_cycle_ownership
    ]

    create_score_table(df_synth_households, household_rows,
                       'output/scores/latex/synthpop_dhwz_households_results_table.tex', True, True)


def score_3_type_households(df: pd.DataFrame) -> List[ComparisonTuple]:
    df_expected = read_marginal_data(['single_person', 'with_children', 'without_children'], 'small_hh_type').set_index(
            ['neighb_code', 'small_hh_type'])
    df_observed = synthetic_population_to_contingency(df, ['neighb_code', 'small_hh_type'], True)[['count']]

    return [(df_observed, df_expected, 'household type', 'neighborhood')]


def score_postal_code(df: pd.DataFrame) -> List[ComparisonTuple]:
    df_expected = read_pc6_data().set_index(['neighb_code', 'PC6'])
    df_observed = synthetic_population_to_contingency(df, ['neighb_code', 'PC6'], False)
    return [(df_observed, df_expected, 'postal code', 'neighborhood')]


def score_income_group(df: pd.DataFrame) -> List[ComparisonTuple]:
    df_contingency = fit_joint_household_income(df)

    rows = []
    for dimension in hh_income_margin_names:
        df_observed = df_contingency.groupby(dimension + ['income_group'])[['count']].sum()
        df_expected = synthetic_population_to_contingency(df, dimension + ['income_group'], True)
        rows.append((df_observed, df_expected, 'income_group', readable_name(dimension, 'income_group')))

    return rows


def score_car_ownership(df: pd.DataFrame) -> List[ComparisonTuple]:
    df_contingency = fit_vehicle_ownership_for_type(df, 'car', df['car_license'].max())
    df_contingency.rename(columns={'n_vehicles': 'cars'}, inplace=True)

    rows = []
    for dimension in get_vehicle_ownership_dimensions('car'):
        df_observed = df_contingency.groupby(dimension + ['cars'])[['count']].sum()
        df_expected = synthetic_population_to_contingency(df, dimension + ['cars'], True)
        rows.append((df_observed, df_expected, 'cars', readable_name(dimension, 'cars')))

    return rows


def score_motor_cycle_ownership(df: pd.DataFrame) -> List[ComparisonTuple]:
    df_contingency = fit_vehicle_ownership_for_type(df, 'motorcycle', df['motorcycle_license'].max())
    df_contingency.rename(columns={'n_vehicles': 'motorcycles'}, inplace=True)

    rows = []
    for dimension in get_vehicle_ownership_dimensions('motorcycle'):
        df_observed = df_contingency.groupby(dimension + ['motorcycles'])[['count']].sum()
        df_expected = synthetic_population_to_contingency(df, dimension + ['motorcycles'], True)
        rows.append((df_observed, df_expected, 'motorcycles', readable_name(dimension, 'motorcycles')))

    return rows
