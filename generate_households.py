import os
import re
from typing import Callable, Literal, Optional, Tuple

import pandas as pd

from attributes.household.household_composition import (get_mother_age_disparity, read_couples_age_disparity,
                                                        read_couples_gender_disparity)
from attributes.household.household_income import (add_household_type_and_income_age_group, fit_joint_household_income,
                                                   hh_income_margin_names)
from attributes.household.post_code import read_pc6_data
from attributes.household.vehicle_ownership import fit_vehicle_ownership_for_type, get_vehicle_ownership_dimensions
from gensynthpop.conditional_attribute_adder import ConditionalAttributeAdder
from gensynthpop.evaluation.validation import validate_synthetic_population_fit
from gensynthpop.household_grouper import HouseholdGrouper, HouseholdType
from gensynthpop.utils.extractors import synthetic_population_to_contingency
from reporting.household_reporting import create_household_score_table


def partition_households(df_synth_pop: pd.DataFrame, _: Optional[pd.DataFrame] = None
                         ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df_couple_age_distribution = read_couples_age_disparity()
    df_couple_gender_distribution = read_couples_gender_disparity()
    df_parent_child_age_distribution = get_mother_age_disparity()

    ##########################################3
    #
    #       MARRIED
    #
    ##########################################3

    # 'married_with_1_children'
    # 'child_in_married_with_1_children'
    married_with_1_children = HouseholdType(
            'married_with_1_children', df_couple_gender_distribution,
            df_couple_age_distribution,
            df_parent_child_age_distribution
    ).add_members(
            'child_in_married_with_1_children', 'child', 1, []
    ).add_members('married_with_1_children', 'adult', 2, ['married_no_children', 'non_married_no_children', 'single'])

    # 'married_with_2_children'
    # 'child_in_married_with_2_children'
    married_with_2_children = HouseholdType(
            'married_with_2_children', df_couple_gender_distribution,
            df_couple_age_distribution,
            df_parent_child_age_distribution
    ).add_members(
            'child_in_married_with_2_children', 'child', 2, []
    ).add_members('married_with_2_children', 'adult', 2, ['married_no_children', 'non_married_no_children', 'single'])

    # 'married_with_3_children'
    # 'child_in_married_with_3_children'
    married_with_3_children = HouseholdType(
            'married_with_3_children', df_couple_gender_distribution,
            df_couple_age_distribution,
            df_parent_child_age_distribution
    ).add_members(
            'child_in_married_with_3_children', 'child', 3, []
    ).add_members('married_with_3_children', 'adult', 2, ['married_no_children', 'non_married_no_children', 'single'])

    ##########################################3
    #
    #       NON-MARRIED
    #
    ##########################################3
    # 'non_married_with_1_children'
    # 'child_in_non_married_with_1_children'
    non_married_with_1_children = HouseholdType(
            'non_married_with_1_children', df_couple_gender_distribution,
            df_couple_age_distribution,
            df_parent_child_age_distribution
    ).add_members(
            'child_in_non_married_with_1_children', 'child', 1, []
    ).add_members(
            'non_married_with_1_children', 'adult', 2, ['non_married_no_children', 'married_no_children', 'single']
    )

    # 'non_married_with_2_children'
    # 'child_in_non_married_with_2_children'
    non_married_with_2_children = HouseholdType(
            'non_married_with_2_children', df_couple_gender_distribution,
            df_couple_age_distribution,
            df_parent_child_age_distribution
    ).add_members(
            'child_in_non_married_with_2_children', 'child', 2, []
    ).add_members(
            'non_married_with_2_children', 'adult', 2, ['non_married_no_children', 'married_no_children', 'single']
    )

    # 'non_married_with_3_children'
    # 'child_in_non_married_with_3_children'
    non_married_with_3_children = HouseholdType(
            'non_married_with_3_children', df_couple_gender_distribution,
            df_couple_age_distribution,
            df_parent_child_age_distribution
    ).add_members(
            'child_in_non_married_with_3_children', 'child', 3, []
    ).add_members(
            'non_married_with_3_children', 'adult', 2, ['non_married_no_children', 'married_no_children', 'single']
    )

    ##########################################3
    #
    #       SINGLE PARENTS
    #
    ##########################################3
    # 'single_parent_1_children'
    # 'child_of_single_parent_1_children'
    single_parent_1_children = HouseholdType(
            'single_parent_1_children', df_couple_gender_distribution, df_couple_age_distribution,
            df_parent_child_age_distribution
    ).add_members(
            'child_of_single_parent_1_children', 'child', 1, []
    ).add_members(
            'single_parent_1_children', 'adult', 1, ['single']
    )

    # 'single_parent_2_children'
    # 'child_of_single_parent_2_children'
    single_parent_2_children = HouseholdType(
            'single_parent_2_children', df_couple_gender_distribution, df_couple_age_distribution,
            df_parent_child_age_distribution
    ).add_members(
            'child_of_single_parent_2_children', 'child', 2, []
    ).add_members(
            'single_parent_2_children', 'adult', 1, ['single']
    )

    # 'single_parent_3_children'
    # 'child_of_single_parent_3_children'
    single_parent_3_children = HouseholdType(
            'single_parent_3_children', df_couple_gender_distribution, df_couple_age_distribution,
            df_parent_child_age_distribution
    ).add_members(
            'child_of_single_parent_3_children', 'child', 3, []
    ).add_members(
            'single_parent_3_children', 'adult', 1, ['single']
    )

    ##########################################3
    #
    #       COUPLES WITHOUT CHILDREN
    #
    ##########################################3

    married_couple_no_children = HouseholdType(
            'married_no_children', df_couple_gender_distribution, df_couple_age_distribution,
            df_parent_child_age_distribution
    ).add_members(
            'married_no_children', 'adult', 2, ['single']
    )

    non_married_couple_no_children = HouseholdType(
            'non_married_no_children', df_couple_gender_distribution, df_couple_age_distribution,
            df_parent_child_age_distribution
    ).add_members(
            'non_married_no_children', 'adult', 2, ['single']
    )

    ##########################################3
    #
    #       SINGLES
    #
    ##########################################3

    singles_household = HouseholdType(
            'single', df_couple_gender_distribution, df_couple_age_distribution,
            df_parent_child_age_distribution
    ).add_members(
            'single', 'adult', 1, []
    )

    ##########################################3
    #
    #       Perform household composition
    #
    ##########################################3
    hh_grouper = HouseholdGrouper(df_synth_pop, ['neighb_code'], 'household_position')

    # married_with_1_children + child_in_married_with_1_children
    hh_grouper.add_household_type(married_with_1_children)
    # married_with_2_children + child_in_married_with_2_children
    hh_grouper.add_household_type(married_with_2_children)
    # married_with_3_children + child_in_married_with_3_children
    hh_grouper.add_household_type(married_with_3_children)

    # non_married_with_1_children + child_in_non_married_with_1_children
    hh_grouper.add_household_type(non_married_with_1_children)
    # non_married_with_2_children + child_in_non_married_with_2_children
    hh_grouper.add_household_type(non_married_with_2_children)
    # non_married_with_3_children + child_in_non_married_with_3_children
    hh_grouper.add_household_type(non_married_with_3_children)

    # single_parent_1_children + child_of_single_parent_1_children
    hh_grouper.add_household_type(single_parent_1_children)
    # single_parent_2_children + child_of_single_parent_2_children
    hh_grouper.add_household_type(single_parent_2_children)
    # single_parent_3_children + child_of_single_parent_3_children
    hh_grouper.add_household_type(single_parent_3_children)

    # married_no_children
    hh_grouper.add_household_type(married_couple_no_children)
    # non_married_no_children
    hh_grouper.add_household_type(non_married_couple_no_children)

    # single
    hh_grouper.add_household_type(singles_household)

    return hh_grouper.run()


def perform_stage(version: int,
                  action: Callable[[pd.DataFrame, Optional[pd.DataFrame]], Tuple[pd.DataFrame, pd.DataFrame]],
                  df_synth_pop: pd.DataFrame, df_synth_households: Optional[pd.DataFrame]
                  ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    pop_template = 'output/synthetic_population/with_households/individuals/synth_pop_DHWZ_v{version}.{extension}'
    hh_template = 'output/synthetic_population/with_households/households/synth_households_DHWZ_v{version}.{extension}'

    pop_exists = os.path.exists(pop_template.format(version=version, extension="pkl"))
    hh_exists = os.path.exists(hh_template.format(version=version, extension="pkl"))

    print(f"Performing stage {version} by calling {action.__name__}")
    if pop_exists and hh_exists:
        print("Reading existing file")
        df_synth_pop = pd.read_pickle(pop_template.format(version=version, extension="pkl"))
        df_synth_households = pd.read_pickle(hh_template.format(version=version, extension="pkl"))
    else:
        df_synth_pop, df_synth_households = action(df_synth_pop, df_synth_households)

        df_synth_pop.to_pickle(pop_template.format(version=version, extension="pkl"))
        df_synth_pop.to_csv(pop_template.format(version=version, extension="csv"))

        df_synth_households.to_pickle(hh_template.format(version=version, extension="pkl"))
        df_synth_households.to_csv(hh_template.format(version=version, extension="csv"))

    return df_synth_pop, df_synth_households


def correct_household_assignment(
        df_synth_pop: pd.DataFrame, df_synth_households: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    The household composition in step one can result in households with a different composition than intended
    (just by merit of trying to place everybody in a household).

    We need to correct the household label to match the actual household composition

    Args:
        df_synth_pop:
        df_synth_households:

    Returns:

    """

    m_no_children = ((df_synth_households.hh_type.isin(
            ['married_with_1_children', 'married_with_2_children', 'married_with_3_children'])
                     ) & (df_synth_households.hh_size == 2)), 'married_no_children'

    m_1_children = ((df_synth_households.hh_type.isin(['married_with_2_children', 'married_with_3_children'])) & (
            df_synth_households.hh_size == 3)), 'married_with_1_children'
    m_2_children = ((df_synth_households.hh_type.isin(['married_with_3_children'])) & (
            df_synth_households.hh_size == 4)), 'married_with_2_children'

    nm_no_children = ((df_synth_households.hh_type.isin(['non_married_with_1_children', 'non_married_with_2_children',
                                                         'non_married_with_3_children'])) & (
                              df_synth_households.hh_size == 2)), 'non_married_no_children'
    nm_1_children = (
            (df_synth_households.hh_type.isin(['non_married_with_2_children', 'non_married_with_3_children'])) & (
            df_synth_households.hh_size == 3)), 'non_married_with_1_children'
    nm_2_children = (
            (df_synth_households.hh_type.isin(['non_married_with_3_children'])) & (
            df_synth_households.hh_size == 4)), 'non_married_with_2_children'

    single_no_children = (
            (df_synth_households.hh_type.isin(
                    ['single_parent_1_children', 'single_parent_2_children', 'single_parent_3_children'])) & (
                    df_synth_households.hh_size == 1)), 'single'
    single_1_children = (
            (df_synth_households.hh_type.isin(['single_parent_2_children', 'single_parent_3_children'])) & (
            df_synth_households.hh_size == 2)), 'single_parent_1_children'
    single_2_children = (
            (df_synth_households.hh_type.isin(['single_parent_3_children'])) & (
            df_synth_households.hh_size == 3)), 'single_parent_2_children'

    for msk, position in [m_no_children, m_1_children, m_2_children, nm_no_children, nm_1_children, nm_2_children,
                          single_no_children, single_1_children, single_2_children]:
        print(f"Adjusting {msk.sum()} households to {position}")
        df_synth_households.loc[msk, 'hh_type'] = position

    return df_synth_pop, df_synth_households


def create_3_type_household_labels(
        df_synth_pop: pd.DataFrame, df_synth_households: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    In order to compare the household types in each neighborhood, we need to map them to the labels used there.
    There are three labels: with children, without children and single households

    Args:
        df_synth_pop:
        df_synth_households:

    Returns:

    """

    def map_to_3_household_types(row):
        if "married" in row.hh_type and "with" in row.hh_type and row.hh_size > 2:
            row.small_hh_type = "with_children"
        elif "single_parent" in row.hh_type and row.hh_size > 1:
            row.small_hh_type = "with_children"
        elif row.hh_size == 1:
            row.small_hh_type = "single_person"
        else:
            row.small_hh_type = "without_children"
        return row

    df_synth_households.loc[:, 'small_hh_type'] = None
    df_synth_households = df_synth_households.apply(map_to_3_household_types, axis=1)

    assert df_synth_households.small_hh_type.isna().sum() == 0

    return df_synth_pop, df_synth_households


def reassign_individual_household_position(
        df_synth_pop: pd.DataFrame, df_synth_households: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    There are 7 household positions reported to the CBS data:
        'child', 'single', 'non_married_no_children', 'married_no_children', 'non_married_with_children',
        'married_with_children', 'single_parent'

    We want to assign these positions based on the household type dataframe.

    We also want to recreate the positions with the 1, 2 or 3 children distinction.

    The agents have been partitioned into households based on these positions. However, after the household assignment,
    their position may have changed. We now assign the correct label again

    Returns:
    """

    df = df_synth_pop.merge(df_synth_households.hh_type, how='left', left_on='household_id', right_index=True)
    df.loc[:, 'n_children'] = df.hh_type.str.replace(
            r'.*(no|\d)_children', r'\1', regex=True
    )

    df.loc[:, 'household_position'] = df.apply(lambda x:
                                               re.sub(r'(\d|no)_children', f"{x.n_children}_children",
                                                      x.household_position), axis=1)

    df.drop(['hh_type', 'n_children'], axis=1, inplace=True)

    return df, df_synth_households


def add_postal_code(df_synth_pop: pd.DataFrame, df_synth_households: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df_contingency = read_pc6_data()

    df = ConditionalAttributeAdder(
            df_synth_households,
            df_contingency,
            'PC6',
            ['neighb_code']
    ).run()

    validate_synthetic_population_fit(
            df,
            df_contingency,
            ['neighb_code', 'PC6'],
            "PC6"
    )

    return df_synth_pop, df


def add_income_household_type(
        df_synth_pop: pd.DataFrame, df_synth_households: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Income is conditioned on age and migration background of the person that is responsible for the primary income.
    For the purposes of this synthetic population, we assume this is just the oldest person in the household.
    If data were available, a more informed decision could perhaps be made here. This is out of scope for now.

    Args:
        df_synth_pop:
        df_synth_households:

    Returns:

    """
    df_principle_income_agents = df_synth_pop.loc[
        df_synth_pop.groupby('household_id')['age'].idxmax(), ['household_id', 'age', 'migration_background']]
    df_principle_income_agents.rename(
            columns={'age': 'main_bread_winner_age', 'migration_background': 'main_bread_winner_migration_background'},
            inplace=True)
    df_synth_households = df_synth_households.merge(df_principle_income_agents, how='left', on='household_id')
    return df_synth_pop, df_synth_households


def add_household_income(
        df_synth_pop: pd.DataFrame, df_synth_households: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df_synth_households = add_household_type_and_income_age_group(df_synth_households)
    df_contingency = fit_joint_household_income(df_synth_households)

    margins = [synthetic_population_to_contingency(
            df_synth_households, ['neighb_code'] + dm, True
    ).reset_index() for dm in hh_income_margin_names]

    df = ConditionalAttributeAdder(
            df_synth_households,
            df_contingency,
            'income_group',
            ['neighb_code']
    ).add_margins(
            margins,
            hh_income_margin_names
    ).run()

    validate_synthetic_population_fit(
            df,
            df_contingency,
            hh_income_margin_names[-1] + ['income_group'],
            'income_group'
    )

    return df_synth_pop, df


def add_number_of_licenses(df_synth_pop: pd.DataFrame, df_synth_households: pd.DataFrame) -> Tuple[
    pd.DataFrame, pd.DataFrame]:
    df_reference = df_synth_pop.replace({'yes': 1, 'no': 0})
    df = df_synth_households.merge(df_reference.groupby('household_id')[['car_license', 'motorcycle_license']].sum(),
                                   on='household_id')

    return df_synth_pop, df


def add_vehicle_ownership(
        vehicle_type: Literal['car', 'motorcycle'],
        df_synth_pop: pd.DataFrame, df_synth_households: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if not 'vehicle_ownership_income_group' in df_synth_pop.columns:
        df_synth_households.loc[:, 'vehicle_ownership_income_group'] = df_synth_households.income_group.map(
                lambda x: int(int(x) / 2) + int(x) % 2)

    max_license = df_synth_households[f'{vehicle_type}_license'].max()
    df_contingency = fit_vehicle_ownership_for_type(df_synth_households, vehicle_type, max_license)
    df_contingency.rename(columns={'n_vehicles': f'{vehicle_type}s'}, inplace=True)

    dimensions = get_vehicle_ownership_dimensions(vehicle_type)
    margins = [synthetic_population_to_contingency(df_synth_households, ['neighb_code'] + dm, True).reset_index()
               for dm in dimensions]

    df = ConditionalAttributeAdder(
            df_synth_households,
            df_contingency,
            f'{vehicle_type}s',
            ['neighb_code']
    ).add_margins(
            margins,
            dimensions
    ).run()

    for dimension in dimensions:
        validate_synthetic_population_fit(
                df,
                df_contingency.groupby(dimension + [f'{vehicle_type}s'])['count'].sum().reset_index(),
                dimension + [f'{vehicle_type}s'],
                f'{vehicle_type}s'
        )

    return df_synth_pop, df


if __name__ == "__main__":
    # Start from the individual attribute population generated with `gensynthpop_dhwz.py`, which has 11 iterations
    df_synth_pop_iteration = pd.read_pickle('output/synthetic_population/individuals/synth_pop_DHWZ_v11.pkl')
    df_synth_household_iteration = None

    stages = [
        partition_households,
        correct_household_assignment,
        create_3_type_household_labels,
        reassign_individual_household_position,
        add_postal_code,
        add_income_household_type,
        add_household_income,
        add_number_of_licenses,
        lambda *args: add_vehicle_ownership('car', *args),
        lambda *args: add_vehicle_ownership('motorcycle', *args),
    ]

    for v, stage in enumerate(stages):
        df_synth_pop_iteration, df_synth_household_iteration = perform_stage(
                v + 1, stage, df_synth_pop_iteration, df_synth_household_iteration)

    create_household_score_table(df_synth_pop_iteration, df_synth_household_iteration)
