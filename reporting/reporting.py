from typing import List

import pandas as pd

from attributes.individual.drivers_license import (get_and_fit_car_driver_license,
                                                   get_and_fit_conditional_moped_license,
                                                   get_and_fit_motor_cycle_license)
from attributes.individual.education.current_education import (current_education_margin_names,
                                                               fit_joint_current_education)
from attributes.individual.education.education_attainment import (add_3_categories_education_level,
                                                                  fit_joint_absolved_education,
                                                                  get_education_attainment_margins)
from attributes.individual.gender import fit_joint_age_gender
from attributes.individual.household_position.household_position import (fit_household_position_joint_age_gender,
                                                                         read_households_margins)
from attributes.individual.integer_age import fit_df_integer_age
from attributes.individual.migration_background import (fit_df_migration_background,
                                                        read_df_migration_background_marginal)
from attributes.marginal_data_reader import age_groups, read_marginal_data
from data_tools.static_mappings import household_map
from gensynthpop.evaluation.reporting import ComparisonTuple, create_score_table, export_distributions_from_rows
from gensynthpop.utils.extractors import synthetic_population_to_contingency


def score_synthetic_population(df_synth_pop: pd.DataFrame):
    rows = [
        score_table_age_group,
        score_table_gender,
        score_table_integer_age,
        # score_table_migration_background,
        # score_absolved_education,
        # score_current_eduction,
        # score_car_drivers_license,
        # score_motor_cycle_drivers_license,
        # score_moped_drivers_license,
        # score_table_household_position
    ]
    create_score_table(df_synth_pop, rows, 'output/scores/latex/synthpop_dhwz_results_table.tex', True, True)
    export_distributions_from_rows(df_synth_pop, rows, 'output/distributions')


def score_table_age_group(df: pd.DataFrame) -> List[ComparisonTuple]:
    df_age_group_expected = read_marginal_data(age_groups, 'age_group').set_index(["neighb_code", "age_group"])["count"]
    print(df_age_group_expected)
    df_age_group_observed = synthetic_population_to_contingency(df, ["neighb_code", "age_group"], full_crostab=True)
    print(df_age_group_observed)
    return [(df_age_group_observed, df_age_group_expected, "age_group", "neighborhood")]


def score_table_gender(df: pd.DataFrame) -> List[ComparisonTuple]:
    df_gender_expected_joint = fit_joint_age_gender().set_index(["age_group", "gender"])
    df_gender_expected_margins = read_marginal_data(
            ["male", "female"], "gender"
    ).set_index(["neighb_code", "gender"])["count"]

    df_gender_observed_joint = synthetic_population_to_contingency(df, ["age_group", "gender"], full_crostab=True)
    df_gender_observed_margins = synthetic_population_to_contingency(df, ["neighb_code", "gender"], full_crostab=True)

    return [
        (df_gender_observed_margins, df_gender_expected_margins, "gender", "neighborhood"),
        (df_gender_observed_joint, df_gender_expected_joint, "gender", "age group")
    ]


def score_table_integer_age(df: pd.DataFrame) -> List[ComparisonTuple]:
    """
    Technically, integer age is also conditioned on age group. However, the scores are exactly the same when age group
    is included in both rows as when it is left out, so not included in the table.

    Args:
        df:

    Returns:

    """
    expected_joint = fit_df_integer_age()
    expected_gender = expected_joint.groupby(['age', 'gender']).sum()["count"]
    expected_margins = expected_joint.groupby(['age']).sum()["count"]

    observed_gender = synthetic_population_to_contingency(df, ["age", "gender"], full_crostab=True)
    observed_margins = synthetic_population_to_contingency(df, ["age"])

    return [
        (observed_margins, expected_margins, "integer", "age"),
        (observed_gender, expected_gender, "integer age", "gender"),
    ]


def score_table_migration_background(df: pd.DataFrame) -> List[ComparisonTuple]:
    expected_margins = read_df_migration_background_marginal().set_index(["neighb_code", "migration_background"])
    expected_joint = fit_df_migration_background(df)
    expected_age_group = expected_joint.groupby(['migration_background', 'small_age_group']).sum()["count"]
    expected_gender = expected_joint.groupby(['migration_background', 'gender']).sum()["count"]

    observed_margins = synthetic_population_to_contingency(df, ["neighb_code", "migration_background"],
                                                           full_crostab=True)
    observed_joint = synthetic_population_to_contingency(df, ["small_age_group", "gender", "migration_background"],
                                                         full_crostab=True)
    observed_age_group = synthetic_population_to_contingency(df, ["small_age_group", "migration_background"],
                                                             full_crostab=True)
    observed_gender = synthetic_population_to_contingency(df, ["gender", "migration_background"], full_crostab=True)

    return [
        (observed_margins, expected_margins, "migration background", "neighborhood"),
        (observed_age_group, expected_age_group, "migration background", "age group"),
        (observed_gender, expected_gender, "migration background", "gender"),
        (
            observed_joint,
            expected_joint.set_index(["small_age_group", "gender", "migration_background"]),
            "migration background",
            r"age group $\times$ gender"
        )
    ]


def score_absolved_education(df: pd.DataFrame) -> List[ComparisonTuple]:
    expected_joint = fit_joint_absolved_education(df)

    margin_names = [
        ["absolved_education"],
        ["education_attainment_age_group", "absolved_education"],
        ["gender", "absolved_education"],
        ["education_attainment_age_group", "gender", "absolved_education"],
    ]

    scores = list()

    for name in margin_names:
        observed = synthetic_population_to_contingency(df, list(name), len(name) > 1)
        expected = expected_joint.groupby(list(name))["count"].sum()

        score = (observed, expected, "absolved education", readable_name(name, "absolved_education"))
        scores.append(score)

    # Check neighborhood margins as well
    _df = add_3_categories_education_level(df.copy())

    observed = synthetic_population_to_contingency(_df, ["absolved_edu_3_cats", "neighb_code"], True)
    expected = get_education_attainment_margins().set_index(['absolved_edu_3_cats', 'neighb_code'])
    score = (observed, expected, "absolved education", "neighborhood")
    scores.insert(1, score)

    return scores


def score_current_eduction(df: pd.DataFrame) -> List[ComparisonTuple]:
    expected_joint = fit_joint_current_education(df)

    margin_names = [['current_education']] + [margin + ['current_education'] for margin in
                                              current_education_margin_names]

    scores: List[ComparisonTuple] = list()

    for name in margin_names:
        observed = synthetic_population_to_contingency(df, list(name), len(name) > 1)
        expected = expected_joint.groupby(list(name))["count"].sum()

        score = (observed, expected, "current education", readable_name(name, "current_education"))
        scores.append(score)

    return scores


def score_car_drivers_license(df: pd.DataFrame) -> List[ComparisonTuple]:
    expected_joint_car = get_and_fit_car_driver_license(df)
    observed_joint_car = synthetic_population_to_contingency(df, ["license_age", "car_license"], True)
    expected_car = expected_joint_car.groupby(['car_license']).sum()
    observed_car = synthetic_population_to_contingency(df, ["car_license"], False)

    return [
        (observed_car, expected_car, "car license", ""),
        (observed_joint_car, expected_joint_car.set_index(['license_age', 'car_license']), "car license", "age")
    ]


def score_motor_cycle_drivers_license(df: pd.DataFrame) -> List[ComparisonTuple]:
    expected_joint_motor_cycle = get_and_fit_motor_cycle_license(df)
    observed_joint_motor_cycle = synthetic_population_to_contingency(df, ['license_age', 'motorcycle_license'])
    expected_motor_cycle = expected_joint_motor_cycle.groupby(['motorcycle_license']).sum()
    observed_motor_cycle = synthetic_population_to_contingency(df, ["motorcycle_license"], False)

    return [
        (observed_motor_cycle, expected_motor_cycle, "motor cycle license", ""),
        (observed_joint_motor_cycle, expected_joint_motor_cycle.set_index(['license_age', 'motorcycle_license']),
         "motor cycle license", "age"),
    ]


def score_moped_drivers_license(df: pd.DataFrame) -> List[ComparisonTuple]:
    expected_joint_moped = get_and_fit_conditional_moped_license(df)
    observed_joint_moped = synthetic_population_to_contingency(df, ['license_age', 'car_license', 'moped_license'])

    expected_joint_moped_age = expected_joint_moped.groupby(['license_age', 'moped_license'])["count"].sum()
    observed_joint_moped_age = synthetic_population_to_contingency(df, ['license_age', 'moped_license'], True)

    expected_joint_moped_car = expected_joint_moped.groupby(['car_license', 'moped_license'])["count"].sum()
    observed_joint_moped_car = synthetic_population_to_contingency(df, ['car_license', 'moped_license'], True)

    expected_moped = expected_joint_moped.groupby(['moped_license'])["count"].sum()
    observed_moped = synthetic_population_to_contingency(df, ["moped_license"], False)

    return [
        (observed_moped, expected_moped, "moped license", ""),
        (observed_joint_moped_age, expected_joint_moped_age, "moped license", "age"),
        (observed_joint_moped_car, expected_joint_moped_car, "moped license", "car license"),
        (observed_joint_moped, expected_joint_moped.set_index(['license_age', 'car_license', 'moped_license']),
         "moped license", r"age $\times$ car license"),
    ]


def score_table_household_position(df: pd.DataFrame) -> List[ComparisonTuple]:
    expected_joint = fit_household_position_joint_age_gender(df)
    expected_age_group = expected_joint.groupby(["household_position", "small_age_group"]).sum()["count"]
    expected_gender = expected_joint.groupby(["household_position", "gender"]).sum()["count"]
    expected_household = read_households_margins().set_index(['neighb_code', 'household_type'])

    observed_joint = synthetic_population_to_contingency(df, ["household_position", "small_age_group", "gender"],
                                                         True)
    observed_age_group = synthetic_population_to_contingency(df, ["household_position", "small_age_group"], True)
    observed_gender = synthetic_population_to_contingency(df, ["household_position", "gender"], True)

    observed_household = synthetic_population_to_contingency(
            df, ["neighb_code", "household_position"],
            True).reset_index().replace(
            household_map
    ).rename(
            columns={'household_position': 'household_type'}
    ).groupby(['neighb_code', 'household_type'])[["count"]].sum()

    expected_marginal = expected_joint.groupby('household_position')['count'].sum()
    observed_marginal = synthetic_population_to_contingency(df, ['household_position'], False)

    return [
        (observed_marginal, expected_marginal, "household position", ""),
        (observed_household, expected_household, "household position", "neighborhood"),
        (observed_age_group, expected_age_group, "household position", "age group"),
        (observed_gender, expected_gender, "household position", "gender"),
        (observed_joint,
         expected_joint.set_index(["household_position", "gender", "small_age_group"]),
         "household position", r"age group $\times$ gender")
    ]


def readable_name(names, dimension):
    if not isinstance(dimension, list):
        dimension = [dimension]
    names = [name for name in names if name not in dimension]
    for i, name in enumerate(names):
        names[i] = "age group" if "age" in name else name.replace("_", " ")
    return r' $\times$ '.join(names)
