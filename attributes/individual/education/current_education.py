import numbers
import os

import pandas as pd
from ipfn import ipfn

from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import get_margin_series_from_synthetic_population


def add_education_age_group(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a column to the synthetic population with the same age groups as used in the current_education data, so
    we can join on that.

    Args:
        df_synth_pop:

    Returns:

    """
    df_synth_pop.loc[:, "education_age_group"] = df_synth_pop.age.transform(lambda x: str(x))
    df_synth_pop.astype({'education_age_group': 'object'})
    for five_year_step in range(30, 95, 5):
        df_synth_pop.loc[
            (df_synth_pop.age >= five_year_step) & (df_synth_pop.age < five_year_step + 5),
            "education_age_group"
        ] = f"{five_year_step}-{five_year_step + 5}"
    df_synth_pop.education_age_group.replace({str(i): "95+" for i in range(95, 101)}, inplace=True)
    df_synth_pop.education_age_group.replace({str(i): "0-4" for i in range(0, 4)}, inplace=True)
    return df_synth_pop


def read_joint_current_education() -> pd.DataFrame:
    """
    ~~See the current_education.ipynb notebook for details on the data.~~
    Update: See the `joint_current_with_attained_education.ipynb` notebook instead. It turns out adding this attribute
    _after_ the absolved/attained education is better, because for the latter, we have neighborhood margins.

    The data set is a combination of three separate data sets, and manipulated to add the missing counts for number
    of people not currently enrolled in education.
    """
    data_path = os.path.join(os.path.dirname(__file__),
                             'processed/prepared_education_conditioned_on_absolved_education.pkl')
    df = pd.read_pickle(data_path).rename(columns={'age': 'education_age_group'})
    return df


def fit_joint_current_education(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    df_current_education_joint = read_joint_current_education()

    margins_dict = get_margin_series_from_synthetic_population(df_synth_pop, current_education_margin_names)
    aggregates = [margins_dict[tuple(names)] for names in current_education_margin_names]

    df_fitted = ipfn.ipfn(
            df_current_education_joint,
            aggregates=aggregates,
            dimensions=current_education_margin_names,
            weight_col='count'
    ).iteration()

    # During evaluation, we use a Z² metric that adds a continuity factor in case the expected value is non-zero.
    # However, there are some extremely small non-zero values in the fitted data frame. Because those values have to
    # be mapped to integers to represent individuals when this attribute is added to the synthetic population, we should
    # expect these values to be mapped to 0. Then the Z-score itself is small (which is fine), but the continuity
    # factor is relatively huge. With many of these groups with such minor differences, the Z² score grows rapidly.
    # We could collapse all values smaller than 0.5 to 0 (or just round all values here to integers). However,
    # to minimize the effect of our meddling, we only apply this to 100 times smaller expected values than that.
    df_fitted = df_fitted.map(lambda x: 0 if (isinstance(x, numbers.Number) and float(x) < 0.005) else x)

    # Validate
    name = "current education X gender X age X migration background x absolved education"
    for names in current_education_margin_names:
        validate_fitted_distribution(df_fitted, margins_dict[tuple(names)], names, name)

    return df_fitted


current_education_margin_names = [
    # Single margins
    ['gender'],
    ["education_age_group"],
    ["migration_background"],
    ["absolved_education"],

    # Double margins
    ["education_age_group", "gender"],
    ["education_age_group", "migration_background"],
    ["education_age_group", "absolved_education"],
    ["gender", "migration_background"],
    ["gender", "absolved_education"],
    ["migration_background", "absolved_education"],

    # Triple margins
    ["education_age_group", "gender", "migration_background"],
    ["education_age_group", "gender", "absolved_education"],
    ["education_age_group", "migration_background", "absolved_education"],
    ["gender", "migration_background", "absolved_education"],

    # Complete margins
    ["education_age_group", "gender", "migration_background", "absolved_education"]
]
