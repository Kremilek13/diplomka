import itertools
import os

import pandas as pd
from ipfn import ipfn

from attributes.code_list import code_list_age_group, code_list_gender, code_list_frequency_activity
from attributes.marginal_data_reader import age_groups, read_marginal_data
from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import synthetic_population_to_contingency

def read_frequency_activity() -> pd.DataFrame:
    data_path = os.path.join(
            os.path.dirname(__file__),
            '../../datasources/individual/commute/frekvence_celkem.csv'
    )
    df = pd.read_csv(data_path, sep=";")
    df = df.rename(columns={"vekova_skupina": "age_group", "pohlavi":"gender", "frekvence_def":"frequency_activity"})
    code_list_age_group(df)
    code_list_gender(df)
    code_list_frequency_activity(df)

    return df


def fit_frequency_activity(df_synth_pop) -> pd.DataFrame:
    df = read_frequency_activity().groupby(['age_group', 'gender', 'ea_school_work', 'frequency_activity'])['count'].sum().reset_index()

    margins_gender = read_marginal_data(['male', 'female'], 'gender').groupby('gender')['count'].sum()
    margins_age = read_marginal_data(age_groups, 'age_group').groupby('age_group')['count'].sum()
    margins_ea_school_work = synthetic_population_to_contingency(df_synth_pop, ["ea_school_work"])["count"]
    margins_gender_age_activity_type = synthetic_population_to_contingency(df_synth_pop, ["gender", "age_group", "ea_school_work"])["count"]
    
    margins_activity = read_df_activity_frequency_marginal().groupby('frequency_activity')['count'].sum()

    # Unikátní hodnoty pro tvorbu mřížky
    ages = df['age_group'].unique()
    genders = df['gender'].unique()
    activities = df['ea_school_work'].unique()
    frequencies = df['frequency_activity'].unique()

    # === 2. NAFOUKNUTÍ MARGINÁLŮ (aby neházel KeyError) ===
    # Vytvoříme index se všemi kombinacemi a ty chybějící vyplníme 0.001
    kompletni_index_marginal = pd.MultiIndex.from_product(
        [genders, ages, activities], 
        names=["gender", "age_group", "ea_school_work"]
    )
    margins_gender_age_activity_type = margins_gender_age_activity_type.reindex(kompletni_index_marginal, fill_value=0)
    # =======================================================

    # === 3. NAFOUKNUTÍ SEED MATICE (aby neházel KeyError u df) ===
    vsechny_kombinace = list(itertools.product(ages, genders, activities, frequencies))
    df_vsechny = pd.DataFrame(vsechny_kombinace, columns=['age_group', 'gender', 'ea_school_work', 'frequency_activity'])

    df = pd.merge(df_vsechny, df, on=['age_group', 'gender', 'ea_school_work', 'frequency_activity'], how='left')
    df['count'] = df['count'].fillna(0.000000000001)
    df["count"] = df["count"].astype(float)
    df = df.groupby(['age_group', 'gender', 'ea_school_work', 'frequency_activity'])['count'].sum().reset_index()
    print(df.to_string())
    # =======================================================
    df_fitted = ipfn.ipfn(
            df.copy().astype({'count': 'float'}),
            aggregates=[margins_age, margins_gender, margins_ea_school_work, margins_activity, margins_gender_age_activity_type],
            dimensions=[['age_group'], ['gender'], ['ea_school_work'], ['frequency_activity'], ['gender','age_group', 'ea_school_work']],
            weight_col='count'
    ).iteration()
    
    name = "frequency_activity X age group X gender X ea_school_work"
    validate_fitted_distribution(df_fitted, margins_age, "age_group", name)
    validate_fitted_distribution(df_fitted, margins_gender, "gender", name)
    validate_fitted_distribution(df_fitted, margins_ea_school_work, 'ea_school_work', name)
    validate_fitted_distribution(df_fitted, margins_activity, 'frequency_activity', name)
    validate_fitted_distribution(df_fitted, margins_gender_age_activity_type, ['gender', 'age_group', 'ea_school_work'], name)

    return df_fitted

def read_df_activity_frequency_marginal() -> pd.DataFrame:
    df_activity_frequency_marginal = read_marginal_data(
        ['work_frequency_5_more_times', 'work_frequency_1_4_times', 'work_frequency_less', 'work_frequency_irregular', 'work_frequency_other_than_op', 
         'work_frequency_undefined',
         'no_stable_job', 'not_working', 'unknown_work_status',
         'school_frequency_5_more_times', 'school_frequency_1_4_times', 'school_frequency_less', 'school_frequency_irregular', 'school_frequency_other_than_op',
         'school_frequency_undefined',
         'school_not_attending', 'unknown_school_status', 
         'economical_activity_unemployed', 'economical_activity_nonworking_retired', 'economical_activity_selfsufficient', 
         'economical_activity_preschool_others_dependent', 'economical_activity_parental_leave', 'economical_activity_undefined'
         ],
        'frequency_activity'
    )

    mapping = {
        'work_frequency_5_more_times':'5_or_more_times',
        'school_frequency_5_more_times':'5_or_more_times',
        'work_frequency_1_4_times':'1_4_times',
        'school_frequency_1_4_times':'1_4_times',
        'work_frequency_less':'regularly',
        'school_frequency_less':'regularly',
        'work_frequency_irregular':'irregularly',
        'school_frequency_irregular':'irregularly',
        'work_frequency_other_than_op':'different_place',
        'school_frequency_other_than_op':'different_place',
        'work_frequency_undefined':'not_determined',
        'school_frequency_undefined':'not_determined',
        'no_stable_job': 'not_moving',
        'not_working': 'not_moving',
        'unknown_work_status': 'not_determined',
        'school_not_attending': 'not_moving',
        'unknown_school_status': 'not_determined',
        'economical_activity_unemployed': 'not_moving',
        'economical_activity_nonworking_retired': 'not_moving',
        'economical_activity_selfsufficient': 'not_moving',
        'economical_activity_preschool_others_dependent': 'not_moving',
        'economical_activity_parental_leave': 'not_moving',
        'economical_activity_undefined': 'not_determined'

    }

    df_activity_frequency_marginal['frequency_activity'] = df_activity_frequency_marginal['frequency_activity'].replace(mapping)

    # 2. Sloučíme a sečteme data
    # (Tím se např. sečte 'work_abroad' a 'school_abroad' do jednoho 'abroad' pro každý neighb_code)
    df_activity_frequency_marginal = df_activity_frequency_marginal.groupby(
        ['neighb_code', 'frequency_activity'], 
        as_index=False
    )['count'].sum()
    
    # 3. Filtruj marginály — odstraň 'abroad' pro věkovou skupinu 0-14
    # (V datech misto_celkova.csv se 0-14 s abroad neobjevuje)
    # Pro teď: odstraň všechny řádky kde place_activity='abroad' a age_group='0-14'
    # (budeme to muset mergovat s age_group, ale to je v fit_place_activity — tam to można udělat lépe)

    return df_activity_frequency_marginal
