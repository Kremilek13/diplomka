import itertools
import os

import pandas as pd
from ipfn import ipfn

from attributes.code_list import code_list_age_group, code_list_gender, code_list_vehicle_activity
from attributes.marginal_data_reader import age_groups, read_marginal_data
from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import synthetic_population_to_contingency

def read_vehicle_activity() -> pd.DataFrame:
    data_path = os.path.join(
            os.path.dirname(__file__),
            '../../datasources/individual/commute/dopravni_prostredek_2.csv'
    )
    df = pd.read_csv(data_path, sep=";")
    df = df.rename(columns={"vekova_skupina": "age_group", "pohlavi":"gender", "dopravni_prostredek_hlavni":"vehicle_activity"})
    code_list_age_group(df)
    code_list_gender(df)
    code_list_vehicle_activity(df)

    return df


def fit_vehicle_activity(df_synth_pop) -> pd.DataFrame:
    df = read_vehicle_activity().groupby(['age_group', 'gender', 'ea_school_work_2', 'category_place_activity', 'category_f_activity', 'vehicle_activity'])['count'].sum().reset_index()

    margins_gender = read_marginal_data(['male', 'female'], 'gender').groupby('gender')['count'].sum()
    margins_age = read_marginal_data(age_groups, 'age_group').groupby('age_group')['count'].sum()
    margins_ea_school_work_2 = synthetic_population_to_contingency(df_synth_pop, ["ea_school_work_2"])["count"]
    margins_category_place_activity = synthetic_population_to_contingency(df_synth_pop, ['category_place_activity'])['count']
    margins_f_activity = synthetic_population_to_contingency(df_synth_pop, ["category_f_activity"])['count']
    margins_gender_age_activity_category_type = synthetic_population_to_contingency(df_synth_pop, ["gender", "age_group", "ea_school_work_2", 'category_place_activity', 'category_f_activity'])["count"]
    
    margins_activity = read_df_activity_vehicle_marginal().groupby('vehicle_activity')['count'].sum()

    # Unikátní hodnoty pro tvorbu mřížky
    ages = df['age_group'].unique()
    genders = df['gender'].unique()
    activities = df['ea_school_work_2'].unique()
    categories_place_activity = df['category_place_activity'].unique()
    fs = df_synth_pop['category_f_activity'].unique()
    vehicles = df['vehicle_activity'].unique()

    # === 2. NAFOUKNUTÍ MARGINÁLŮ (aby neházel KeyError) ===
    # Vytvoříme index se všemi kombinacemi a ty chybějící vyplníme 0.001
    kompletni_index_marginal = pd.MultiIndex.from_product(
        [genders, ages, activities, categories_place_activity, fs], 
        names=["gender", "age_group", "ea_school_work_2", "category_place_activity", "category_f_activity"]
    )
    margins_gender_age_activity_category_type = margins_gender_age_activity_category_type.reindex(kompletni_index_marginal, fill_value=0)
    # =======================================================

    # === 3. NAFOUKNUTÍ SEED MATICE (aby neházel KeyError u df) ===
    vsechny_kombinace = list(itertools.product(ages, genders, activities, categories_place_activity, fs, vehicles))
    df_vsechny = pd.DataFrame(vsechny_kombinace, columns=['age_group', 'gender', 'ea_school_work_2', 'category_place_activity', "category_f_activity", 'vehicle_activity'])

    df = pd.merge(df_vsechny, df, on=['age_group', 'gender', 'ea_school_work_2', 'category_place_activity', "category_f_activity", 'vehicle_activity'], how='left')
    df['count'] = df['count'].fillna(0.000000000001)
    maska_nesmysl = ((df['category_place_activity'] == 'not_moving') | (df['category_f_activity'] == 'not_moving')) & (df['vehicle_activity'] != 'not_moving')
    df.loc[maska_nesmysl, 'count'] = 0
    df["count"] = df["count"].astype(float)
    df = df.groupby(['age_group', 'gender', 'ea_school_work_2', 'category_place_activity', 'category_f_activity', 'vehicle_activity'])['count'].sum().reset_index()
    print(df.to_string())
    # =======================================================
    df_fitted = ipfn.ipfn(
            df.copy().astype({'count': 'float'}),
            aggregates=[margins_age, margins_gender, margins_ea_school_work_2, margins_category_place_activity, margins_f_activity, margins_activity, margins_gender_age_activity_category_type],
            dimensions=[['age_group'], ['gender'], ['ea_school_work_2'], ['category_place_activity'], ['category_f_activity'], ['vehicle_activity'], ['gender','age_group', 'ea_school_work_2', 'category_place_activity', 'category_f_activity']],
            weight_col='count'
    ).iteration()
    
    name = "vehicle_activity X age group X gender X ea_school_work_2"
    validate_fitted_distribution(df_fitted, margins_age, "age_group", name)
    validate_fitted_distribution(df_fitted, margins_gender, "gender", name)
    validate_fitted_distribution(df_fitted, margins_ea_school_work_2, 'ea_school_work_2', name)
    validate_fitted_distribution(df_fitted, margins_category_place_activity, 'category_place_activity', name)
    validate_fitted_distribution(df_fitted, margins_f_activity, 'category_f_activity', name)
    validate_fitted_distribution(df_fitted, margins_activity, 'vehicle_activity', name)
    validate_fitted_distribution(df_fitted, margins_gender_age_activity_category_type, ['gender', 'age_group', 'ea_school_work_2', 'category_place_activity', 'category_f_activity'], name)

    return df_fitted

def read_df_activity_vehicle_marginal() -> pd.DataFrame:
    df_activity_vehicle_marginal = read_marginal_data(
        ['transport_car_driver', 'transport_car_passenger', 'transport_public', 'transport_bus', 'transport_train','transport_motorcycle',
         'transport_bicycle', 'transport_other', 'transport_none_walking', 'transport_undefined',
         'no_stable_job', 'not_working', 'unknown_work_status',
         
         'school_not_attending', 'unknown_school_status', 
         'economical_activity_unemployed', 'economical_activity_nonworking_retired', 'economical_activity_selfsufficient', 
         'economical_activity_preschool_others_dependent', 'economical_activity_parental_leave', 'economical_activity_undefined'
         ],
        'vehicle_activity'
    )

    mapping = {
        'transport_car_driver':'driver',
        'transport_car_passenger':'shotgun',
        'transport_public':'city_public_transport',
        'transport_bus':'bus',
        'transport_train':'train',
        'transport_motorcycle':'motorbike',
        'transport_bicycle':'bicycle',
        'transport_other':'other',
        'transport_none_walking':'nothing',
        'transport_undefined':'not_determined',

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

    df_activity_vehicle_marginal['vehicle_activity'] = df_activity_vehicle_marginal['vehicle_activity'].replace(mapping)

    # 2. Sloučíme a sečteme data
    # (Tím se např. sečte 'work_abroad' a 'school_abroad' do jednoho 'abroad' pro každý neighb_code)
    df_activity_vehicle_marginal = df_activity_vehicle_marginal.groupby(
        ['neighb_code', 'vehicle_activity'], 
        as_index=False
    )['count'].sum()
    
    # 3. Filtruj marginály — odstraň 'abroad' pro věkovou skupinu 0-14
    # (V datech misto_celkova.csv se 0-14 s abroad neobjevuje)
    # Pro teď: odstraň všechny řádky kde place_activity='abroad' a age_group='0-14'
    # (budeme to muset mergovat s age_group, ale to je v fit_place_activity — tam to można udělat lépe)

    return df_activity_vehicle_marginal
