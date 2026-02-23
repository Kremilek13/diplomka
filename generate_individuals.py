import os
from typing import Callable, Optional

import pandas as pd

from attributes.delete_unknown import replace_value
from attributes.individual.commute import fit_place_activity, read_df_activity_place_marginal
from attributes.individual.drivers_license import (add_license_age_to_synthetic_population,
                                                   get_and_fit_car_driver_license,
                                                   get_and_fit_conditional_moped_license,
                                                   get_and_fit_motor_cycle_license)
from attributes.individual.economical_activity import (fit_activity, read_df_activity_marginal, activity_0_14)
from attributes.individual.education_cz import (fit_edu, fit_specific_education, read_df_education_marginal)
from attributes.individual.education.current_education import (add_education_age_group, current_education_margin_names,
                                                               fit_joint_current_education)
from attributes.individual.education.education_attainment import (add_education_attainment_age_group,
                                                                  fit_joint_absolved_education,
                                                                  get_education_attainment_margins)
from attributes.individual.gender import fit_joint_age_gender
from attributes.individual.household_position.household_position import (fit_household_position_joint_age_gender,
                                                                         read_households_margins)
from attributes.individual.integer_age import fit_df_integer_age
from attributes.individual.migration_background import (add_small_age_group, fit_df_migration_background,
                                                        read_df_migration_background_marginal)
from attributes.marginal_data_reader import age_groups, read_marginal_data
from gensynthpop.conditional_attribute_adder import ConditionalAttributeAdder
from gensynthpop.evaluation.validation import validate_synthetic_population_fit
from gensynthpop.utils.extractors import (get_margin_frames_from_synthetic_population,
                                          synthetic_population_to_contingency)
from reporting.reporting import score_synthetic_population

def instantiate_population(_=None) -> pd.DataFrame:
    """
    Kick-starts the population synthesis by instantiating the reported number of agents in each
    of the used neighborhoods and assigning them a unique ID

    Returns:

    """
    print("Instantiating Synthetic Population")
    agent_ids = list()
    agent_neighborhoods = list()
    agent_count = 0
    for neighb_code, (neighb_total) in read_marginal_data(['population'], 'population').iterrows():
        agent_ids += [f"SA{i + agent_count:06d}" for i in range(neighb_total.iloc[0])]
        agent_neighborhoods += [neighb_code] * neighb_total.iloc[0]
        agent_count += neighb_total.iloc[0]
    return pd.DataFrame(data=dict(agent_id=agent_ids, neighb_code=agent_neighborhoods))


def add_age_group(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    print("Adding age group")
    df_age_group = read_marginal_data(age_groups, 'age_group')
    print(df_age_group)
    df = ConditionalAttributeAdder(
            df_synthetic_population=df_synth_pop,
            df_contingency=df_age_group,
            target_attribute='age_group',
            group_by=['neighb_code']
    ).run()

    validate_synthetic_population_fit(df, df_age_group, ["neighb_code", "age_group"], "age_group")

    return df


def add_gender_conditionally(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    """
    Adds gender conditioned on age group.
    Age group has already been added to the synthetic population.
    Gender is available from the marginal data per neighborhood.
    An age_group X gender joint distribution is available at the municipality level.

    Args:
        df_synth_pop:

    Returns:

    """
    print("Adding gender conditioned on age group")
    df_contingency = fit_joint_age_gender()
    df_margins_age_group = read_marginal_data(age_groups, 'age_group')
    df_margins_gender = read_marginal_data(['male', 'female'], 'gender')

    df = ConditionalAttributeAdder(
            df_synthetic_population=df_synth_pop,
            df_contingency=df_contingency,
            target_attribute="gender",
            group_by=["neighb_code"]
    ).add_margins(
            margins=[df_margins_age_group, df_margins_gender],
            margins_names=[["age_group"], ["gender"]]
    ).run()

    # The rest is evaluation
    validate_synthetic_population_fit(df, df_margins_age_group, ["neighb_code", "age_group"], "gender")
    validate_synthetic_population_fit(df, df_margins_gender, ["neighb_code", "gender"], "gender")

    # Note we compare to the fitted joint distribution, because unless the original joint distribution is congruent
    # with the previous data sources used, we cannot reasonably expect to match all used distributions and margins
    validate_synthetic_population_fit(df, df_contingency, ["age_group", "gender"], "gender")

    return df


def add_integer_age_conditionally(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    """
    Adds integer age conditioned on age group and gender.
    Age group and gender have already been added to the synthetic population.


    Args:
        df_synth_pop:

    Returns:

    """
    print("Adding integer age conditioned on age group and gender")
    df_contingency = fit_df_integer_age()

    df = ConditionalAttributeAdder(
            df_synth_pop,
            df_contingency,
            "age",
            ["neighb_code"]
    ).add_margins(
            [read_marginal_data(age_groups, "age_group"), read_marginal_data(["male", "female"], "gender")],
            [["age_group"], ["gender"]]
    ).run()

    # Note we compare to the fitted joint distribution, because unless the original joint distribution is congruent
    # with the previous data sources used, we cannot reasonably expect to match all used distributions and margins
    validate_synthetic_population_fit(df, df_contingency, ["age_group", "gender", "age"], "age")

    return df


def add_migration_background(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    """
    Adds migration background (Dutch, Western, NonWestern) conditioned on gender and age, but with margins of each
    migration background group provided per neighborhood.

    Note, the margins use different age groups than the joint distribution, so integer age is mapped to the appropriate
    age groups.

    Args:
        df_synth_pop:

    Returns:
    """
    print("Adding migration background conditioned on age and gender")

    df_synth_pop = add_small_age_group(df_synth_pop)
    df_contingency = fit_df_migration_background(df_synth_pop)

    margins_gender = read_marginal_data(['male', 'female'], 'gender')
    margins_age_group = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "small_age_group"],
                                                            True).reset_index()
    margins_gender_age = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "gender", "small_age_group"],
                                                             True).reset_index()
    margins_migration_background = read_df_migration_background_marginal()

    df = ConditionalAttributeAdder(
            df_synth_pop,
            df_contingency,
            "migration_background",
            ["neighb_code"]
    ).add_margins(
            [margins_gender, margins_age_group, margins_migration_background, margins_gender_age],
            [["gender"], ["small_age_group"], ["migration_background"], ["gender", "small_age_group"]]
    ).run()

    validate_synthetic_population_fit(
            df,
            margins_migration_background,
            ["neighb_code", "migration_background"],
            "migration_background"
    )

    validate_synthetic_population_fit(
            df,
            df_contingency,
            ["small_age_group", "gender", "migration_background"],
            "migration_background"
    )

    return df


def add_absolved_education(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    df_synth_pop = add_education_attainment_age_group(df_synth_pop)
    df_contingency = fit_joint_absolved_education(df_synth_pop)

    # Single margins
    margins_gender = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "gender"], True).reset_index()
    margins_age = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "education_attainment_age_group"],
                                                      True).reset_index()
    margins_absolved_edu_3_cats = get_education_attainment_margins()

    # Double margins
    margins_gender_age = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "gender",
                                                                            "education_attainment_age_group"],
                                                             True).reset_index()

    df = ConditionalAttributeAdder(
            df_synth_pop,
            df_contingency,
            "absolved_education",
            ["neighb_code"]
    ).add_margins(
            [
                margins_gender,
                margins_age,
                margins_absolved_edu_3_cats,
                margins_gender_age,
            ],
            [
                ["gender"],
                ["education_attainment_age_group"],
                ["absolved_edu_3_cats"],
                ["education_attainment_age_group", "gender"],
            ]
    ).run()

    validate_synthetic_population_fit(df, df_contingency,
                                      ["gender", "education_attainment_age_group", "absolved_education"],
                                      "absolved_education")

    return df


def add_current_education(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    df_synth_pop = add_education_age_group(df_synth_pop)
    df_contingency = fit_joint_current_education(df_synth_pop)

    margins_dict = get_margin_frames_from_synthetic_population(
            df_synth_pop,
            [['neighb_code'] + names for names in current_education_margin_names]
    )
    aggregates = [margins_dict[tuple(['neighb_code'] + names)] for names in current_education_margin_names]

    df = ConditionalAttributeAdder(
            df_synth_pop,
            df_contingency,
            "current_education",
            ["neighb_code"]
    ).add_margins(
            aggregates,
            current_education_margin_names
    ).run()

    validate_synthetic_population_fit(
            df,
            df_contingency,
            ["education_age_group", "gender", "migration_background", "absolved_education", "current_education"],
            "current_education"
    )

    return df


def add_car_drivers_license(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    df_synth_pop = add_license_age_to_synthetic_population(df_synth_pop)

    df_car = get_and_fit_car_driver_license(df_synth_pop)

    margins_age = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "license_age"], True).reset_index()

    df = ConditionalAttributeAdder(
            df_synth_pop,
            df_car,
            "car_license",
            ["neighb_code"]
    ).add_margins(
            [margins_age],
            [["license_age"]]
    ).run()

    validate_synthetic_population_fit(
            df,
            df_car,
            ["license_age", "car_license"],
            "car_license"
    )

    return df


def add_motor_cycle_drivers_license(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    df_motor_cycle = get_and_fit_motor_cycle_license(df_synth_pop)
    margins_age = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "license_age"], True).reset_index()

    df = ConditionalAttributeAdder(
            df_synth_pop,
            df_motor_cycle,
            "motorcycle_license",
            ["neighb_code"]
    ).add_margins(
            [margins_age],
            [["license_age"]]
    ).run()

    validate_synthetic_population_fit(
            df,
            df_motor_cycle,
            ["license_age", "motorcycle_license"],
            "motorcycle_license"
    )

    return df


def add_moped_drivers_license(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    df_moped = get_and_fit_conditional_moped_license(df_synth_pop)

    margins_age = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "license_age"], True).reset_index()
    margins_car = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "car_license"], True).reset_index()
    margins_age_car = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "license_age", "car_license"],
                                                          True).reset_index()

    df = ConditionalAttributeAdder(
            df_synth_pop,
            df_moped,
            "moped_license",
            ["neighb_code"]
    ).add_margins(
            [margins_age, margins_car, margins_age_car],
            [['license_age'], ['car_license'], ['license_age', 'car_license']]
    ).run()

    validate_synthetic_population_fit(
            df,
            df_moped,
            ["license_age", "car_license", "moped_license"],
            "moped_license"
    )

    return df


def add_household_position(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    """
    Uses household information to determine the fraction of agents within each age and gender group that are children

    Args:
        df_synth_pop:

    Returns:
    """
    print("household position conditioned on age group, gender and household type")
    df_synth_pop = add_small_age_group(df_synth_pop)
    df_contingency = fit_household_position_joint_age_gender(df_synth_pop)
    
    margins_gender = read_marginal_data(['male', 'female'], 'gender')
    margins_age_group = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "small_age_group"],
                                                            True).reset_index()
    margins_gender_age = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "gender", "small_age_group"],
                                                             True).reset_index()
    margins_household_type = read_households_margins()

    df = ConditionalAttributeAdder(
            df_synth_pop,
            df_contingency,
            "household_position",
            ["neighb_code"]
    ).add_margins(
            [margins_gender, margins_age_group, margins_gender_age, margins_household_type],
            [["gender"], ["small_age_group"], ["gender", "small_age_group"], ['household_type']]
    ).run()

    validate_synthetic_population_fit(
            df,
            df_contingency,
            ["small_age_group", "gender", "household_position"],
            "household_position"
    )

    return df


def perform_stage(version: int, action: Callable[[Optional[pd.DataFrame]], pd.DataFrame],
                  *arg: pd.DataFrame) -> pd.DataFrame:
    output_template = (
        'output/synthetic_population/individuals/synth_pop_DHWZ_v{version}.{extension}')

    print(f"Performing stage {version} by calling {action.__name__}")
    if os.path.exists(output_template.format(version=version, extension="pkl")):
        df = pd.read_pickle(output_template.format(version=version, extension="pkl"))
    else:
        df = action(*arg)
        df.to_pickle(output_template.format(version=version, extension="pkl"))
        df.to_csv(output_template.format(version=version, extension="csv"))
    df = df.sample(frac=1).reset_index(drop=True)

    return df


def delete_previous_results():
    output_folder = [
                        'output/synthetic_population/individuals/', 
                        'output/distributions/'
                        ]
    for output_folder in output_folder:
        for file in os.listdir(output_folder):
                # if file.startswith("synth_pop_DHWZ_v"):
                os.remove(os.path.join(output_folder, file))
        print(f"Deleted previous results in {output_folder}")
    
    
def add_absolved_education_conditionally(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    """
    Adds education conditioned on age group and gender.
    Age group and gender have already been added to the synthetic population.


    Args:
        df_synth_pop:

    Returns:

    """
    df_contingency = fit_edu(df_synth_pop)
    margins_gender = read_marginal_data(['male', 'female'], 'gender')
    margins_age_group = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "age_group"], True).reset_index()
    margins_gender_age = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "gender", "age_group"], True).reset_index()   
    margins_education = read_df_education_marginal()

    df = ConditionalAttributeAdder(
            df_synth_pop,
            df_contingency,
            "education",
            ["neighb_code"]
    ).add_margins(
            [margins_gender,
             margins_age_group, 
             margins_education,
             margins_gender_age],
            [["gender"], ["age_group"], ["education"], 
             ["gender", "age_group"]]
    ).run()
    
    validate_synthetic_population_fit(df, df_contingency, ["age_group", "gender", "education"], "education")

    return df

def add_specific_education_conditionally(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    """
    Adds specific education conditioned on age group, gender and general education.
    Age group, gender and coarse education have already been added to the synthetic population.
    """
    print("Adding specific education conditioned on age group, gender and general education")
    
    df_contingency = fit_specific_education(df_synth_pop)
    df_contingency = df_contingency.rename(columns={'education_coarse': 'education'})

    margins_gender = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "gender"], True).reset_index()
    margins_age_group = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "age_group"], True).reset_index()
    margins_gender_age = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "gender", "age_group"],True).reset_index()
    margins_education_coarse = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "education"], True).reset_index()

    df = ConditionalAttributeAdder(
            df_synthetic_population=df_synth_pop,
            df_contingency=df_contingency,
            target_attribute="education_specific", 
            group_by=["neighb_code"]
    ).add_margins(
            [margins_gender, 
            margins_age_group, 
            margins_education_coarse, 
            margins_gender_age],
            [["gender"], ["age_group"], ["education"], ["gender", "age_group"]]
    ).run()
    
    validate_synthetic_population_fit(
        df, 
        df_contingency, 
        ["age_group", "gender", "education", "education_specific"], 
        "education_specific"
    )

    return df

def add_economical_activity(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    """
    Adds economical activity conditioned on age group and gender.
    Age group and gender have already been added to the synthetic population.


    Args:
        df_synth_pop:

    Returns:

    """
    print("Adding economical activity conditioned on age group and gender")
    df_contingency = fit_activity(df_synth_pop)
    margins_gender = read_marginal_data(['male', 'female'], 'gender')
    margins_age_group = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "age_group"],
                                                            True).reset_index()
    margins_gender_age = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "gender", "age_group"],
                                                             True).reset_index()
    margins_activity = read_df_activity_marginal()


    df = ConditionalAttributeAdder(
            df_synth_pop,
            df_contingency,
            "economical_activity",
            ["neighb_code"]
    ).add_margins(
            [margins_gender,
             margins_age_group, 
             margins_activity,
             margins_gender_age],
            [["gender"], ["age_group"], ["economical_activity"], 
             ["gender", "age_group"]]
    ).run()

    activity_0_14(df)

    validate_synthetic_population_fit(df, df_contingency, ["age_group", "gender", "economical_activity"], "economical_activity")

    return df

def add_ea_for_travelling(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    skola_hodnoty = ['economical_activity_nonworking_students_pupils'] 
    prace_hodnoty = ['economical_activity_maternity_leave', 'economical_activity_employed', 'economical_activity_working_student', 'economical_activity_working_retired']
    bydliste_hodnoty = ['economical_activity_unemployed', 'economical_activity_nonworking_retired', 'economical_activity_selfsufficient', 'economical_activity_parental_leave', 'economical_activity_preschool_others_dependent']

    df_synth_pop['ea_school_work'] = 'nezjištěno'
    df_synth_pop.loc[df_synth_pop['economical_activity'].isin(skola_hodnoty), 'ea_school_work'] = 'school'
    df_synth_pop.loc[df_synth_pop['economical_activity'].isin(prace_hodnoty), 'ea_school_work'] = 'work'
    # use 'not_moving' to match place_activity margin categories (instead of 'residence')
    df_synth_pop.loc[df_synth_pop['economical_activity'].isin(bydliste_hodnoty), 'ea_school_work'] = 'not_moving'

    # Fix invalid combinations: age 0-14 should not have ea_school_work='work'
    # Change them to 'school' if they were assigned 'work'
    # invalid_mask = (df_synth_pop['age_group'] == '0-14') & (df_synth_pop['ea_school_work'] == 'work')
    # if invalid_mask.sum() > 0:
    #     print(f"Warning: Correcting {invalid_mask.sum()} individuals aged 0-14 with ea_school_work='work' -> 'school'")
    #     df_synth_pop.loc[invalid_mask, 'ea_school_work'] = 'school'
    # df_synth_pop = replace_value(df_synth_pop, 'ea_school_work', 'nezjištěno', ['gender', 'age_group', 'neighb_code'])


    return df_synth_pop

def add_commute_destination_conditionally(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    """
    Adds commute destination conditioned on age group, ea_school_work and gender.
    Age group, ea_school_work and gender have already been added to the synthetic population.


    Args:
        df_synth_pop:

    Returns:

    """
    df_contingency = fit_place_activity(df_synth_pop)
    margins_gender = read_marginal_data(['male', 'female'], 'gender')
    margins_age_group = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "age_group"], True).reset_index()
    margins_ea_school_work = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "ea_school_work"], True).reset_index()
    margins_gender_age = synthetic_population_to_contingency(df_synth_pop, ["neighb_code", "gender", "age_group", "ea_school_work"], True).reset_index()   
    margins_activity_place = read_df_activity_place_marginal()

    df = ConditionalAttributeAdder(
            df_synth_pop,
            df_contingency,
            "place_activity",
            ["neighb_code"]
    ).add_margins(
            [margins_gender,
             margins_age_group, 
             margins_activity_place,
             margins_ea_school_work,
             margins_gender_age],
            [["gender"], ["age_group"], ["place_activity"], ["ea_school_work"],
             ["gender", "age_group", "ea_school_work"]]
    ).run()
    
    validate_synthetic_population_fit(df, df_contingency, ["age_group", "gender", "ea_school_work", "place_activity"], "place_activity")

    return df


if __name__ == "__main__":
    # delete_previous_results()

    df_synth_pop_iteration = perform_stage(1, instantiate_population)

    stages = [
        add_age_group,
        add_gender_conditionally,
        add_integer_age_conditionally,
        # add_migration_background,
        # add_absolved_education,
        add_absolved_education_conditionally,
	    add_specific_education_conditionally,
        add_economical_activity,
        add_ea_for_travelling,
        add_commute_destination_conditionally,
        # add_current_education,
        # add_car_drivers_license,
        # add_motor_cycle_drivers_license,
        # add_moped_drivers_license,
        # add_household_position
    ]

    current_version = 2
    for stage in stages:
        df_synth_pop_iteration = perform_stage(current_version, stage, df_synth_pop_iteration)
        current_version += 1

    print("Done! Here is what the synthetic population looks like")
    print(df_synth_pop_iteration.dtypes)
    score_synthetic_population(df_synth_pop_iteration)

    # attributes_to_correct = [
    #     lambda df: replace_value(df, 'education', 'education_undefined', ['gender', 'age_group', 'neighb_code']),
    #     lambda df: replace_value(df, 'economical_activity', 'economical_activity_undefined', ['gender', 'age_group', 'neighb_code']),
    #     lambda df: replace_value(df, 'education_specific', 'nezjištěno', ['gender', 'age_group', 'neighb_code', 'education']),
    #     lambda df: replace_value(df, 'ea_school_work', 'nezjištěno', ['economical_activity'])
    # ]

    # for attribute in attributes_to_correct:
    #     df_synth_pop_iteration = perform_stage(current_version, attribute, df_synth_pop_iteration)
    #     current_version += 1

    print("Final synthetic population after corrections")
