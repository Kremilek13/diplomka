import itertools
import os
import re

import pandas as pd
from ipfn import ipfn

from attributes.individual.commute_place import read_place_activity
from attributes.marginal_data_reader import read_marginal_data
from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import synthetic_population_to_contingency

def add_building_floor_types(df_synth_households: pd.DataFrame) -> pd.DataFrame:
    # Definice skupin (podobně jako u příjmu)
    couple_with_children = [
        'married_with_1_children', 'married_with_2_children', 'married_with_3_children',
        'non_married_with_1_children', 'non_married_with_2_children', 'non_married_with_3_children'
    ]
    single_parent = ['single_parent_1_children', 'single_parent_2_children', 'single_parent_3_children']
    couple_no_children = ['married_no_children', 'non_married_no_children']

    # Mapování na tvoje kategorie z obrázku
    mapping = {hht: 'par_s_detmi' for hht in couple_with_children}
    mapping.update({hht: 'neuplna_rodina' for hht in single_parent})
    mapping.update({hht: 'par_bez_deti' for hht in couple_no_children})
    mapping.update({'single': 'jednotlivec'})

    df_synth_households.loc[:, 'typ_domacnosti_building'] = df_synth_households.hh_type.map(mapping).fillna('ostatni')
    
    return df_synth_households


def read_building_floor_distribution():
    data_path = os.path.join(
            os.path.dirname(__file__),
            "../../datasources/household/building_floor/Brno_domacnost_typ_budovy_filtr.csv"
    )
    df = pd.read_csv(data_path, sep=';')

    df = df.rename(columns={"typ_domacnosti": "typ_domacnosti_building", "typ_budovy":"building_floor", "velikost_domacnosti":"hh_size", "pocet_domacnosti":"count"})

    df.replace({
        'jednotlivec_v_byte': 'jednotlivec',
        'neuplna_rodina_v_byte': 'neuplna_rodina',
        'par_bez_deti_v_byte': 'par_bez_deti',
        'par_s_detmi_v_byte': 'par_s_detmi'
    }, inplace=True)

    return df

def fit_building_floor(df_synth_households: pd.DataFrame) -> pd.DataFrame:
    # 1. Načtení základního seedu
    df = read_building_floor_distribution().groupby(['typ_domacnosti_building', 'hh_size', 'building_floor'])['count'].sum().reset_index()
    
    # 2. Příprava marginálií
    margins_building_floor = read_marginal_building_floor_data().groupby(['building_floor'])['count'].sum()
    margins_size = synthetic_population_to_contingency(df_synth_households, ["hh_size"])["count"]    
    margins_hh_type = synthetic_population_to_contingency(df_synth_households, ["typ_domacnosti_building"])["count"]
    margins_hh_type_size = synthetic_population_to_contingency(df_synth_households, ["typ_domacnosti_building", "hh_size"])["count"]
    

    # Sjednocení typů v margináliích na STRING (prevence KeyError v IPFN)
    margins_size.index = margins_size.index.astype(str)
    margins_hh_type.index = margins_hh_type.index.astype(str)
    margins_building_floor.index = margins_building_floor.index.astype(str)
    
    # Oprava MultiIndexu u margins_hh_type_size
    margins_hh_type_size.index = margins_hh_type_size.index.set_levels([
        margins_hh_type_size.index.levels[0].astype(str), 
        margins_hh_type_size.index.levels[1].astype(str)
    ])

    # Unikátní hodnoty pro nafouknutí seedu
    sizes = df['hh_size'].astype(str).unique()
    types = df['typ_domacnosti_building'].astype(str).unique()
    buildings = margins_building_floor.index.unique() # Bereme z marginálií, aby žádná nechyběla

    # === 3. NAFOUKNUTÍ SEEDU (Fix ValueError a Merge Error) ===
    # POŘADÍ v product musí odpovídat POŘADÍ v columns!
    vsechny_kombinace = list(itertools.product(types, sizes, buildings))
    df_vsechny = pd.DataFrame(vsechny_kombinace, columns=['typ_domacnosti_building', 'hh_size', 'building_floor'])

    # Sjednocení typů na string před mergem
    df['hh_size'] = df['hh_size'].astype(str)
    df['typ_domacnosti_building'] = df['typ_domacnosti_building'].astype(str)
    df['building_floor'] = df['building_floor'].astype(str)

    df = pd.merge(df_vsechny, df, on=['typ_domacnosti_building', 'hh_size', 'building_floor'], how='left')
    df['count'] = df['count'].fillna(0.0001).astype(float)

    # === 4. NAFOUKNUTÍ MULTI-MARGINÁLU (Fix KeyError v IPFN) ===
    kompletni_index_marginal = pd.MultiIndex.from_product(
        [types, sizes], 
        names=["typ_domacnosti_building", "hh_size"]
    )
    margins_hh_type_size = margins_hh_type_size.reindex(kompletni_index_marginal, fill_value=0.0001)

    # Odstranění jmen indexů (IPFN to tak vyžaduje u některých verzí)
    margins_hh_type.index.name = None
    margins_size.index.name = None
    margins_building_floor.index.name = None
    margins_hh_type_size.index.names = [None, None]

    print("Starting IPFN iteration...")
    
    # 5. IPFN volání
    df_fitted = ipfn.ipfn(
            df,
            aggregates=[margins_hh_type, margins_size, margins_building_floor, margins_hh_type_size],
            dimensions=[['typ_domacnosti_building'], ['hh_size'], ['building_floor'], ['typ_domacnosti_building', 'hh_size']],
            weight_col='count'
    ).iteration()

    # Převod hh_size zpět na int pro validaci a další kroky, pokud je potřeba
    df_fitted['hh_size'] = df_fitted['hh_size'].astype(int)

    # Validace
    name = "building_floor fitting"
    # validate_fitted_distribution(df_fitted, margins_size, "hh_size", name)
    validate_fitted_distribution(df_fitted, margins_hh_type, "typ_domacnosti_building", name)
    validate_fitted_distribution(df_fitted, margins_building_floor, 'building_floor', name)

    return df_fitted

def read_marginal_building_floor_data() -> pd.DataFrame:
    # 1. Načtení dat - read_marginal_data vrací "long" formát (tři sloupce: neighb_code, building_floor, count)
    df_long = read_marginal_data(
        [    
            # 'hd_rd_celkem', 
            'hd_rd_1nadzem', 'hd_rd_2nadzem', 'hd_rd_3avicenadzem',
            # 'hd_bd_celkem', 
            'hd_bd_1_2nadzem', 'hd_bd_3_4nadzem', 'hd_bd_5_6nadzem', 
            'hd_bd_7avicenadzem', 
            # 'hd_ostatni_domy_celkem', 
            'hd_ostatni_1_2nadzem',
            'hd_ostatni_3_4nadzem', 'hd_ostatni_5avice_nadzem', 
            # 'hd_druhdomu_nezjisten'
        ],
        'building_floor'
    )
    
    # 2. PIVOT: Rozbalíme to do sloupců, abychom mohli odečítat
    # Index zůstane neighb_code, sloupce budou názvy kategorií
    # df_wide = df_long.reset_index().pivot(index='neighb_code', columns='building_floor', values='count')

    # columns_to_drop = ['hd_rd_celkem', 'hd_bd_celkem', 'hd_ostatni_domy_celkem', 'hd_druhdomu_nezjisten']
    # df_wide = df_wide.drop(columns=columns_to_drop, errors='ignore')

    # # 5. MELT: Zabalíme to zpátky do "long" formátu pro zbytek skriptu
    # df_final = df_wide.reset_index().melt(
    #     id_vars='neighb_code', 
    #     var_name='building_floor', 
    #     value_name='count'
    # )

    mapping ={
        'hd_rd_1nadzem': 'rd_1p',
        'hd_rd_2nadzem': 'rd_2p',
        'hd_rd_3avicenadzem': 'rd_3avicep',
        'hd_bd_1_2nadzem': 'bd_1_2p',
        'hd_bd_3_4nadzem': 'bd_3_4p',
        'hd_bd_5_6nadzem': 'bd_5_6p',
        'hd_bd_7avicenadzem': 'bd_7avicep',
        'hd_ostatni_1_2nadzem': 'ostatni_budovy_1_2p',
        'hd_ostatni_3_4nadzem': 'ostatni_budovy_3_4p',
        'hd_ostatni_5avice_nadzem': 'ostatni_budovy_5avicep'
    }

    df_long['building_floor'] = df_long['building_floor'].replace(mapping)

    return df_long