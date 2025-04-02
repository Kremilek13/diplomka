import os

import pandas as pd
from ipfn import ipfn

from attributes.marginal_data_reader import read_marginal_data
from data_tools.static_mappings import specific_to_grouped_attained_education_map
from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import synthetic_population_to_contingency


def read_joint_education_attainment() -> pd.DataFrame:
    """
    See the education_attainment.ipynb notebook for details on the data.

    The data is manipulated to condition the CBS-provided education attainment counts on current education levels using
    domain knowledge.

    Returns:

    """
    data_path = os.path.join(os.path.dirname(__file__), "processed/prepared_absolved_education.pkl")
    df = pd.read_pickle(data_path).rename(columns={'age': 'education_attainment_age_group'})
    return df


def add_education_attainment_age_group(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    df_synth_pop.loc[:, "education_attainment_age_group"] = df_synth_pop.age.transform(lambda x: str(x))
    df_synth_pop.astype({'education_attainment_age_group': 'object'})
    for five_year_step in range(15, 75, 10):
        df_synth_pop.loc[
            (df_synth_pop.age >= five_year_step) & (df_synth_pop.age < five_year_step + 10),
            "education_attainment_age_group"
        ] = f"{five_year_step}-{five_year_step + 10}"
    df_synth_pop.education_attainment_age_group.replace({str(i): "75+" for i in range(75, 101)}, inplace=True)
    df_synth_pop.education_attainment_age_group.replace({str(i): "0-4" for i in range(0, 4)}, inplace=True)
    return df_synth_pop


def add_3_categories_education_level(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    df_synth_pop.loc[:, ['absolved_edu_3_cats']] = df_synth_pop.absolved_education.map(
            specific_to_grouped_attained_education_map)
    return df_synth_pop


def get_education_attainment_margins():
    margins = read_marginal_data(['education_absolved_low', 'education_absolved_middle', 'education_absolved_high'],
                                 'absolved_edu_3_cats')
    margins.loc[:, 'count'] = pd.to_numeric(margins['count'], errors='coerce').astype('Int64')
    margins.loc[:, 'absolved_edu_3_cats'] = margins.absolved_edu_3_cats.str.replace('education_absolved_', '')

    # Calculate relative frequencies of neighborhoods that are not NAN
    s_totals = margins.groupby('absolved_edu_3_cats')['count'].mean()
    s_totals /= s_totals.sum()

    # Find missing neighborhoods
    missing = margins[margins["count"].isna()].neighb_code.unique()

    # Correct missing neighborhoods
    margins = margins.set_index('absolved_edu_3_cats')
    neighborhood_totals = read_marginal_data(['population'], 'population')
    for neighb_code in missing:
        margins.loc[margins.neighb_code == neighb_code, 'count'] = s_totals * neighborhood_totals.loc[neighb_code][
            'population']

    margins = margins.reset_index().merge(neighborhood_totals, left_on='neighb_code', right_index=True,
                                          how='left').set_index(['neighb_code', 'absolved_edu_3_cats'])
    margins.loc[:, 'count'] = margins.groupby(level=0)["count"].transform(lambda x: x / x.sum()) * margins.population

    return margins.reset_index()[["neighb_code", "absolved_edu_3_cats", "count"]]


def fit_joint_absolved_education(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    """
    Fits the joint education attainment data set provided by `read_joint_education_attainment` to the known margins of
    the synthetic population.

    Returns:

    """
    df_education_attainment_joint = read_joint_education_attainment().groupby(
            ['education_attainment_age_group', 'absolved_edu_3_cats', 'gender',
             'absolved_education']).sum().reset_index()

    # Single
    margins_gender = synthetic_population_to_contingency(df_synth_pop, ["gender"])[
        "count"].astype(float)
    margins_age_group = synthetic_population_to_contingency(df_synth_pop, ["education_attainment_age_group"])[
        "count"].astype(float)
    margins_education_attainment = get_education_attainment_margins().groupby(['absolved_edu_3_cats']).sum()[
        "count"].astype(float)

    # Double
    margins_gender_age = synthetic_population_to_contingency(
            df_synth_pop, ["gender", "education_attainment_age_group"], full_crostab=True)["count"].astype(float)

    margins = {
        ('gender',): margins_gender,
        ('education_attainment_age_group',): margins_age_group,
        ('absolved_edu_3_cats',): margins_education_attainment,
        ('gender', 'education_attainment_age_group'): margins_gender_age,
    }

    margin_names = list(margins.keys())

    df_education_attainment_joint = remove_missing_values(df_education_attainment_joint, margins)

    # Fit
    df_fitted = ipfn.ipfn(
            df_education_attainment_joint,
            aggregates=[margins[name] for name in margin_names],
            dimensions=[list(name) for name in margin_names],
            weight_col='count',
            max_iteration=100000
    ).iteration()

    # Validate
    name = "absolved education X gender X age X current education"
    for margin_name in margin_names:
        validate_fitted_distribution(df_fitted, margins[margin_name], list(margin_name), name)

    return df_fitted


def remove_missing_values(df_contingency, margins):
    """
    Sometimes, a category can have such a low count, that it is not added to the synthetic population at all.
    This is the case for the education level "Specialistenopleiding (niveau 4b)", which in the raw CBS data has just
    6 people enrolled. When the entire data set is scaled down to the size of the synthetic population, the 6 is reduced
    to so close to 0, that it is a better fit not to assign anybody to that education level. In that case, it is missing
    from the synthetic population, and should not be considered in the remainder of the fit, either.

    Args:
        df_contingency:
        margins:

    Returns:

    """
    mask = pd.Series(False, index=df_contingency.index)
    for m in margins:
        if len(m) != 1:
            continue
        not_in_synth_pop = [v for v in df_contingency[m[0]].unique() if v not in margins[m].index.unique()]
        if not_in_synth_pop:
            print(
                    f"The following values from the margin {m} are not present in the synthetic population, "
                    f"and will be "
                    f"removed from the contingency data frame:")
            print("\t", not_in_synth_pop)
            for nisp in not_in_synth_pop:
                mask |= df_contingency[m[0]] == nisp
    return df_contingency.loc[~mask]
