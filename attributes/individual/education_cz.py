import os
import itertools


import pandas as pd
from ipfn import ipfn

from attributes.code_list import code_list_age_group, code_list_gender, code_list_education, create_dictionary
from attributes.marginal_data_reader import age_groups, read_marginal_data
from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import synthetic_population_to_contingency

def read_edu() -> pd.DataFrame:
    data_path = os.path.join(
            os.path.dirname(__file__),
            '../../datasources/individual/education/vzdelani_pohlavi_vek.csv'
    )
    df = pd.read_csv(data_path, sep=",")
    df = df.rename(columns={"vekova_skupina": "age_group", "pohlavi":"gender", "vzdelani":"education", "pocet_obyvatel":"count"})
    code_list_age_group(df)
    code_list_gender(df)
    code_list_education(df, 'kategorie')

    print(df)
    return df


def fit_edu(df_synth_pop) -> pd.DataFrame:
    df = read_edu().groupby(['age_group', 'gender', 'education']).sum().reset_index()
    df["count"] = df["count"].astype(float)

    margins_gender = read_marginal_data(['male', 'female'], 'gender').groupby(['gender']).sum()["count"]
    margins_age = read_marginal_data(age_groups, 'age_group').groupby('age_group').sum()["count"]
    margins_gender_age = synthetic_population_to_contingency(df_synth_pop, ["gender", "age_group"])["count"]
    margins_age_group = synthetic_population_to_contingency(df_synth_pop, ["age_group"])["count"]
    margins_education = read_df_education_marginal().groupby(
            'education'
    )["count"].sum()

    df_fitted = ipfn.ipfn(
            df.copy().astype({'count': 'float'}),
            aggregates=[margins_gender, margins_age_group, margins_education, margins_gender_age],
            dimensions=[['gender'], ['age_group'], ['education'], ['gender','age_group']],
            weight_col='count'
    ).iteration()

    name = "education X age group X gender"
    validate_fitted_distribution(df_fitted, margins_age_group, "age_group", name)
    validate_fitted_distribution(df_fitted, margins_gender, "gender", name)
    validate_fitted_distribution(df_fitted, margins_education, 'education', name)
    validate_fitted_distribution(df_fitted, margins_gender_age, ['gender', 'age_group'], name)


    return df_fitted

def read_df_education_marginal() -> pd.DataFrame:
    df_education_marginal = read_marginal_data(
        ['0-14', 'education_primary_no', 'education_secondary', 'education_higher', 'education_undefined'],
        'education'
    )
    mapping = {
        '0-14': 'education_primary_no'
    }
    df_education_marginal['education'] = df_education_marginal['education'].replace(mapping)
    df_education_marginal = df_education_marginal.groupby(
        [
        'neighb_code', 
        'education'], 
        as_index=False
    )['count'].sum()


    # df_education_marginal = read_marginal_data(
    #     ['education_primary_no', 'education_secondary', 'education_higher', 'education_undefined', 'population'],
    #     'education'
    # ).pivot(
    #         index="neighb_code", columns='education', values='count'
    # )

    # children = df_education_marginal.population - df_education_marginal.education_primary_no - df_education_marginal.education_secondary - df_education_marginal.education_higher - df_education_marginal.education_undefined
    # df_education_marginal['education_primary_no'] = df_education_marginal['education_primary_no'] + children
    # # df_education_marginal.loc[:, ["education_primary_no"]] = children

    # df_education_marginal = df_education_marginal.drop("population", axis=1).reset_index()

    # df_education_marginal = pd.melt(
    #         df_education_marginal,
    #         id_vars=["neighb_code"],
    #         value_vars=["education_primary_no", "education_secondary", "education_higher", "education_undefined"],
    #         value_name="count",
    #         var_name="education"
    # )

    return df_education_marginal

def read_spec_edu() -> pd.DataFrame:
    data_path = os.path.join(
            os.path.dirname(__file__),
            '../../datasources/individual/education/vzdelani_pohlavi_vek.csv'
    )
    df = pd.read_csv(data_path, sep=",")
    df = df.rename(columns={"vekova_skupina": "age_group", "pohlavi":"gender", "vzdelani":"education", "pocet_obyvatel":"count"})
    code_list_age_group(df)
    code_list_gender(df)
    code_list_education(df, 'text')
    df = df.rename(columns={"education":"education_specific"})

    print(df)
    return df

def fit_specific_education(df_synth_pop: pd.DataFrame) -> pd.DataFrame:
    df_specific_education = read_spec_edu() 
    df_specific_education["count"] = df_specific_education["count"].astype(float)

    mapping_dict = create_dictionary()
    df_specific_education['education_coarse'] = df_specific_education['education_specific'].str.strip().map(mapping_dict)

    df_seed = df_specific_education.groupby(
        ['age_group', 'gender', 'education_coarse', 'education_specific']
    )['count'].sum().reset_index()

    margins_gender = synthetic_population_to_contingency(df_synth_pop, ["gender"])["count"]
    margins_age = synthetic_population_to_contingency(df_synth_pop, ["age_group"])["count"]
    margins_coarse_edu = synthetic_population_to_contingency(df_synth_pop, ["education"])["count"]
    margins_gender_age = synthetic_population_to_contingency(df_synth_pop, ["gender", "age_group", "education"])["count"]
    
    margins_coarse_edu.index.name = 'education_coarse'
    ages = df_synth_pop['age_group'].unique()
    genders = df_synth_pop['gender'].unique()
    educations_coarse = df_synth_pop['education'].unique()
    educations = df_seed['education_specific'].unique()

    # === 1. OPRAVA INDEXŮ PRO IPFN ===
    # V populaci se to jmenuje 'education', ale pro IPFN (v seedu) to potřebujeme jako 'education_coarse'
    margins_gender_age.index.names = ["gender", "age_group", "education_coarse"]
    margins_coarse_edu.index.name = 'education_coarse'
    
    kompletni_index_marginal = pd.MultiIndex.from_product(
        [genders, ages, educations_coarse], 
        names=["gender", "age_group", "education_coarse"]
    )
    margins_gender_age = margins_gender_age.reindex(kompletni_index_marginal, fill_value=0)

    # === 2. OPRAVA NAFUKOVACÍ MATICE A MERGE ===
    vsechny_kombinace = list(itertools.product(ages, genders, educations_coarse, educations))
    
    # Tady musíme použít 'education_coarse', aby to sedělo se zbytkem
    df_vsechny = pd.DataFrame(vsechny_kombinace, columns=['age_group', 'gender', 'education_coarse', 'education_specific'])

    # Mergujeme s df_seed (protože ten jde do IPFN), a používáme 'education_coarse'
    df_seed = pd.merge(df_vsechny, df_seed, on=['age_group', 'gender', 'education_coarse', 'education_specific'], how='left')
    df_seed['count'] = df_seed['count'].fillna(0.000000000001)
    df_seed["count"] = df_seed["count"].astype(float)
    
    # Seskupíme, aby to bylo krásně čisté
    df_seed = df_seed.groupby(['age_group', 'gender', 'education_coarse', 'education_specific'])['count'].sum().reset_index()
    # ============================================

    # df_fitted = ipfn.ipfn(
    #         df_seed.copy().astype({'count': 'float'}),
    #         aggregates=[margins_gender, margins_age, margins_gender_age, margins_coarse_edu],
    #         dimensions=[['gender'], ['age_group'], ['gender', 'age_group', 'education_coarse'], ['education_coarse']],
    #         weight_col='count'
    # ).iteration()

    df_fitted = ipfn.ipfn(
            df_seed.copy().astype({'count': 'float'}),
            aggregates=[margins_gender, margins_age, margins_gender_age, margins_coarse_edu],
            dimensions=[['gender'], ['age_group'], ['gender', 'age_group', 'education_coarse'], ['education_coarse']],
            weight_col='count'
    ).iteration()

    name = "specific_edu X coarse_edu X age X gender"
    
    validate_fitted_distribution(df_fitted, margins_age, "age_group", name)
    validate_fitted_distribution(df_fitted, margins_gender, "gender", name)
    validate_fitted_distribution(df_fitted, margins_gender_age, ['gender', 'age_group', 'education_coarse'], name)
    validate_fitted_distribution(df_fitted, margins_coarse_edu, 'education_coarse', name)

    return df_fitted