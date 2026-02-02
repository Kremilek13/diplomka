import os

import pandas as pd
from ipfn import ipfn

from attributes.code_list import code_list_age_group, code_list_gender, code_list_economical_activity
from attributes.marginal_data_reader import age_groups, read_marginal_data
from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import synthetic_population_to_contingency

def read_activity() -> pd.DataFrame:
    data_path = os.path.join(
            os.path.dirname(__file__),
            '../../datasources/individual/economical_activity/EA_pohlavi_vek.csv'
    )
    df = pd.read_csv(data_path, sep=",")
    df = df.rename(columns={"vekova_skupina": "age_group", "pohlavi":"gender", "ekonomicka_aktivita":"economical_activity", "pocet_obyvatel":"count"})
    code_list_age_group(df)
    code_list_gender(df)
    code_list_economical_activity(df)

    print(df)
    return df


def fit_activity(df_synth_pop) -> pd.DataFrame:
    df = read_activity().groupby(['age_group', 'gender', 'economical_activity']).sum().reset_index()
    df["count"] = df["count"].astype(float)

    margins_gender = read_marginal_data(
            ['male', 'female'], 'gender'
    ).groupby(['gender']).sum()["count"]

    margins_age = read_marginal_data(age_groups, 'age_group').groupby('age_group').sum()["count"]

    margins_gender_age = synthetic_population_to_contingency(df_synth_pop, ["gender", "age_group"])["count"]
    margins_age_group = synthetic_population_to_contingency(df_synth_pop, ["age_group"])["count"]
    margins_activity = read_df_activity_marginal().groupby(
            'economical_activity'
    )["count"].sum()

    df_fitted = ipfn.ipfn(
            df.copy().astype({'count': 'float'}),
            aggregates=[margins_gender, margins_age, margins_activity, margins_gender_age],
            dimensions=[['gender'], ['age_group'],  ['economical_activity'], ['gender','age_group']],
            weight_col='count'
    ).iteration()

    name = "economical_activity X age group X gender"
    validate_fitted_distribution(df_fitted, margins_age, "age_group", name)
    validate_fitted_distribution(df_fitted, margins_gender, "gender", name)
    validate_fitted_distribution(df_fitted, margins_activity, 'economical_activity', name)
    validate_fitted_distribution(df_fitted, margins_gender_age, ['gender', 'age_group'], name)

    return df_fitted

def read_df_activity_marginal() -> pd.DataFrame:
    df_activity_marginal = read_marginal_data(
        ['economical_activity_employed', 'economical_activity_working_retired', 
         'economical_activity_working_student', 'economical_activity_maternity_leave', 'economical_activity_parental_leave',
         'economical_activity_unemployed', 'economical_activity_nonworking_retired', 'economical_activity_selfsufficient',
         'economical_activity_preschool_others_dependent', 'economical_activity_nonworking_students_pupils',
         'economical_activity_undefined'],
        'economical_activity'
    )

    return df_activity_marginal

def activity_0_14(df: pd.DataFrame) -> pd.DataFrame:
    print("Analyzing capacity for dependent children based on margins...")

    # --- 1. NASTAVENÍ (Zde si upravte název kategorie) ---
    # Jak se jmenuje ta kategorie v margináliích, kterou chcete testovat?
    # Např. 'economical_activity_other_dependent' nebo 'education_primary_no'
    # Podle předchozí konverzace asi 'education_primary_no' (předškoláci) nebo obecně 'dependent'
    CATEGORY_DEPENDENT = 'economical_activity_preschool_others_dependent' 
    
    COL_TARGET = 'economical_activity'

    # Načteme marginálie
    df_margins = read_marginal_data([CATEGORY_DEPENDENT], 'count').reset_index()
    print(df_margins)
    # df_margins = df_margins.rename(columns={CATEGORY_DEPENDENT: 'count'})
    
    results = []
    unique_neighborhoods = df['neighb_code'].unique()

    for code in unique_neighborhoods:
        # --- A. Cílový počet z marginálií ---
        # Vyfiltrujeme řádek pro danou čtvrť a danou kategorii
        margin_row = df_margins[
            (df_margins['neighb_code'] == code) 
        ]
        
        if margin_row.empty:
            continue
            
        total_target_dependent = margin_row[CATEGORY_DEPENDENT].values[0]

        # --- B. Počet závislých nad 14 let v datech ---
        # Filtrujeme lidi v této čtvrti, kteří jsou > 14 a mají tuto aktivitu
        # (Zde předpokládáme, že dospělí už mají aktivitu přiřazenou správně z předchozích kroků)
        existing_dependents_over_14 = len(df[
            (df['neighb_code'] == code) & 
            (df['age'] > 14) & 
            (df[COL_TARGET] == CATEGORY_DEPENDENT)
        ])

        existing_dependents_under_14 = len(df[
            (df['neighb_code'] == code) & 
            (df['age'] < 15) & 
            (df[COL_TARGET] == CATEGORY_DEPENDENT)
        ])

        # --- C. Kolik míst zbývá pro děti? ---
        slots_for_children = total_target_dependent - existing_dependents_over_14

        # --- D. Kolik máme dětí v různých věkových skupinách? ---
        # Počítáme prostý počet dětí v daném věku v té čtvrti
        df_neighb = df[df['neighb_code'] == code]
        
        count_0_5 = (df_neighb['age'] <= 5).sum()
        count_0_6 = (df_neighb['age'] <= 6).sum()
        count_0_7 = (df_neighb['age'] <= 7).sum()

        # --- E. Výpočet rozdílu (Delta) ---
        # Kladné číslo = zbývá místo, Záporné číslo = dětí je víc než místa
        diff_0_5 = slots_for_children - count_0_5
        diff_0_6 = slots_for_children - count_0_6
        diff_0_7 = slots_for_children - count_0_7

        zero = existing_dependents_under_14 - slots_for_children

        # Najdeme, která varianta je nejblíže nule (nejmenší absolutní rozdíl)
        best_fit_diff = min(abs(diff_0_5), abs(diff_0_6), abs(diff_0_7))
        best_fit_age = ""
        if best_fit_diff == abs(diff_0_5): best_fit_age = "0-5"
        elif best_fit_diff == abs(diff_0_6): best_fit_age = "0-6"
        else: best_fit_age = "0-7"

        results.append({
            'neighb_code': code,
            'target_total': total_target_dependent,
            'occupied_over_14': existing_dependents_over_14,
            'slots_for_kids': slots_for_children,
            'kids_0_5': count_0_5,
            'kids_0_6': count_0_6,
            'kids_0_7': count_0_7,
            'diff_0_5': diff_0_5,
            'diff_0_6': diff_0_6,
            'diff_0_7': diff_0_7,
            'BEST_FIT': best_fit_age,
            'non_fit': existing_dependents_under_14,
            'zero': zero,


        })
        print(results)

        if slots_for_children > existing_dependents_under_14:
            capacity_dependent = max(0, int(slots_for_children)) 
        else:
            capacity_dependent = max(0, int(existing_dependents_under_14))
        # slots_for_children je celkem - důchodci; ale může to nabořit strukturu
        #  možná je lepší použít celkový počet existing_dependents_under_14 - nenabourá strukturu ve věkové skupině 0-14
        CATEGORY_STUDENT = 'economical_activity_nonworking_students_pupils'
        mask_kids = (df['neighb_code'] == code) & (df['age'] >= 0) & (df['age'] <= 14)
        kids_in_hood = df.loc[mask_kids].sort_values(by='age')
        kids_dependent = kids_in_hood.iloc[:capacity_dependent]
        kids_student = kids_in_hood.iloc[capacity_dependent:]

        if not kids_dependent.empty:
            df.loc[kids_dependent.index, COL_TARGET] = CATEGORY_DEPENDENT
        
    # Zapíšeme studenty (školáky)
        if not kids_student.empty:
            df.loc[kids_student.index, COL_TARGET] = CATEGORY_STUDENT
    

    # Vytvoříme přehlednou tabulku
    df_results = pd.DataFrame(results)
    
    # Vypíšeme souhrn
    print("\n--- ANALÝZA KAPACIT PRO ZÁVISLÉ DĚTI ---")
    if not df_results.empty:
        print(df_results[['neighb_code', 'slots_for_kids', 'kids_0_5', 'kids_0_6', 'kids_0_7', 'BEST_FIT', 'non_fit', 'zero']].to_string())
        
        # Celkové doporučení (četnost)
        print("\nDoporučení pro celé město (nejčastější shoda):")
        print(df_results['BEST_FIT'].value_counts())
    return df
    
