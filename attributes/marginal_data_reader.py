import os
import re
from typing import List

import pandas as pd

from gensynthpop.utils.extractors import multicolumn_to_attribute_values


def read_marginal_data(columns: List[str], attribute_name: str) -> pd.DataFrame:
    """
    Takes one attribute, characterised by `columns`, from the core marginal dataset available for DHWZ
    Args:
        columns:
        attribute_name:

    Returns:

    """
    margins_path = os.path.join(os.path.dirname(__file__),
                                '../datasources/marginal/mc_brno.csv')
    df_marginal = pd.read_csv(margins_path, sep=";")
    column_names = [original for original, renamed in marginal_data_code_map.items() if renamed in columns]
    if 'mc' not in column_names:
        column_names.append('mc')
    df_marginal = df_marginal[column_names]
    df_marginal = df_marginal.rename(columns=marginal_data_code_map)
    # df_marginal = df_marginal[df_marginal.neighb_code.isin(neighborhood_codes)]
    print(df_marginal)
    if len(columns) > 1:
        return multicolumn_to_attribute_values(df_marginal, attribute_name, columns)
    else:
        return df_marginal.set_index('neighb_code')


def read_province_population_size():
    """
    Read from https://opendata.cbs.nl/#/CBS/nl/dataset/70072ned/table?dl=A6290

    Returns:
    """
    path = os.path.join(os.path.dirname(__file__),
                        '../datasources/marginal/Regionale_kerncijfers_Nederland_19052024_185018.csv')
    df = pd.read_csv(path, sep=";")
    df = df.rename(columns={
                               c: re.sub(
                                       r'Bevolking/Bevolkingssamenstelling op 1 januari/Leeftijd/Leeftijdsgroepen/('
                                       r'\d+) tot (\d+) jaar \(aantal\)',
                                       r'\1-\2',
                                       c
                               ) for c in df.columns
                           } | {
                               'Bevolking/Bevolkingssamenstelling op 1 januari/Leeftijd/Leeftijdsgroepen/80 jaar of '
                               'ouder (aantal)': '80+',
                               'Bevolking/Bevolkingssamenstelling op 1 januari/Leeftijd/Leeftijdsgroepen/Jonger dan 5 '
                               'jaar (aantal)': '<5',
                               'Bevolking/Bevolkingssamenstelling op 1 januari/Totale bevolking (aantal)': 'total'
                           }).drop(['Perioden', "Regio's"], axis=1).T.rename(columns={0: 'count'})
    df.index.name = 'age'

    assert df.loc['total']["count"] == df[df.index != 'total']["count"].sum(), "CBS data total count mismatch"

    df = df[df.index != 'total']

    return df


# These are the neighborhoods that we want to include
neighborhood_codes = pd.Series(
        [551082, 551325, 551198, 551066, 551317, 551376, 551406, 551074, 551171, 551210, 551147, 551228, 551007, 551287, 551252, 551236, 551112, 551422, 551244, 551031, 551295, 551091, 550973, 551309, 551431, 551279, 550990, 551368, 551058
        ], name="kód")




age_groups = ['0-14', '15-24', '25-44', '45-64', '64+']

# Defines how the column names used by CBS map to more convenient names we can use later.
# May have to be extended if more marginal attributes are used
marginal_data_code_map = {
    'mc': 'neighb_code',
    'pocet_oby': 'population',
    'muzi': 'male',
    'zeny': 'female',
    'oby_0_14': '0-14',
    'oby_15_24': '15-24',
    'oby_25_44': '25-44',
    'oby_45_64': '45-64',
    'oby_65avice': '64+',
    # 'vzd_zaklad_nizsi': 'education_primary_no',
    'vzdel_zaklad_nebonizsi':'education_primary_no',
    'vzdel_stredni': 'education_secondary',
    'vzdel_vs': 'education_higher',
    'vzdel_nezjisteno': 'education_undefined',
    'ea_zamestnanci':'economical_activity_employed',
    'ea_prac_duchod':'economical_activity_working_retired',
    'ea_prac_student':'economical_activity_working_student',
    'ea_md':'economical_activity_maternity_leave',
    'ea_nezam':'economical_activity_unemployed',
    'ea_neprac_duchod':'economical_activity_nonworking_retired',
    'ea_vlastni_zdroj':'economical_activity_selfsufficient',
    'ea_neprac_zaci_studenti':'economical_activity_nonworking_students_pupils',
    'ea_rd': 'economical_activity_parental_leave',
    'ea_predskolni_ostatni_zavisle':'economical_activity_preschool_others_dependent',
    'ea_nezjisteno':'economical_activity_undefined',
    'rs_nezadani': 'unmarried',
    'rs_vdani_rp': 'married',
    'pocet_hd': 'households',
    'hd_jednotlivci': 'single_person',
    'hd_s_jednou_rodinnou_bez_deti': 'without_children',
    'hd_s_jednou_rodinnou_s_detmi': 'with_children', 
    'vyj_zam_vramci_obce': 'work_in_neighborhood',
    'vyj_zam_jinyokres_vkraji': 'work_other_district_same_province',
    'vyj_zam_jinykraj': 'work_other_province',
    'vyj_zam_zahranici': 'work_abroad',
    'zam_bez_staleho_mista': 'no_stable_job',
    'zam_nevyj': 'not_working',
    'vyj_zam_nezjisteno': 'unknown_work_status',
    'vyj_skola_vramci_obce': 'school_in_neighborhood',
    'vyj_skola_jinyokres_vkraji': 'school_other_district_same_province',
    'vyj_skola_jinykraj': 'school_other_province',
    'vyj_skola_zahranici': 'school_abroad',
    'skola_nevyj': 	'school_not_attending', 
    'vyj_skola_nezjisteno':'unknown_school_status'

}
