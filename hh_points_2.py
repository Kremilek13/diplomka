# bobyosl21 - počet lidí podle sčítání lidu 2021
# sum_byt - počet bytů v domě = maximální počet domácností v domě
# pocpodbud - počet podlaží v domě
# zpvybu - 06 = bytový dům, 07 = rodinný dům
# npodl - počet podlaží nad zemí + patra
import geopandas as gpd
import pandas as pd
import numpy as np
import os
import re
import random

# --- KONFIGURACE ---
FLOOR_MAPPING = {
    'rd_1p': (1, 1),
    'rd_2p': (2, 2),
    'rd_3avicep': (3, 100),
    'bd_1_2p': (1, 2), 
    'bd_3_4p': (3, 4),
    'bd_5_6p': (5, 6),
    'bd_7avicep': (7, 100),
    'ostatni_budovy_1_2p': (1, 2),
    'ostatni_budovy_3_4p': (3, 4),
    'ostatni_budovy_5avicep': (5, 100)
}

# --- POMOCNÉ FUNKCE ---

def clean_code(val):
    try:
        return str(int(float(val))).strip()
    except:
        return str(val).strip()

def split_household_building_floor(df_hh: pd.DataFrame) -> pd.DataFrame:
    df_hh['hh_building_type'] = df_hh['building_floor'].apply(lambda x: x.rsplit('_', 1)[0])
    df_hh['hh_floor_range'] = df_hh['building_floor'].apply(lambda x: x.rsplit('_', 1)[1])
    return df_hh

def get_best_floor(hh_full_string, b_res_floors):
    if hh_full_string not in FLOOR_MAPPING or not b_res_floors:
        return random.choice(b_res_floors) if b_res_floors else 1
    f_min, f_max = FLOOR_MAPPING[hh_full_string]
    matching_floors = [f for f in b_res_floors if f_min <= f <= f_max]
    if matching_floors:
        return random.choice(matching_floors)
    return random.choice(b_res_floors)

def check_floor_match(hh_full_string, b_res_floors):
    if hh_full_string not in FLOOR_MAPPING or not b_res_floors:
        return False
    f_min, f_max = FLOOR_MAPPING[hh_full_string]
    for f in b_res_floors:
        if f_min <= f <= f_max: return True
    return False

# --- OPRAVENÁ score_v3: nyní přijímá b_res_floors jako argument ---
def score_v3(hh_size, hh_full_floor, current_pop, target_pop, b_res_floors):
    new_pop = current_pop + hh_size
    diff = new_pop - target_pop
    if diff > 0:
        penalty = diff * 2000   # přeplnění je špatné
    else:
        penalty = abs(diff) * 1000
    # Penalizace za neshodu podlaží
    if not check_floor_match(hh_full_floor, b_res_floors):
        penalty += 50
    return penalty

# --- JÁDRO VÝPOČTU ---

def extract_building_table(gpkg_path: str) -> pd.DataFrame:
    print(f"Načítám budovy z {gpkg_path}...")
    gdf = gpd.read_file(gpkg_path, ignore_geometry=True)
    pattern = re.compile(r'np(\d+)_\d+f')
    np_cols = [c for c in gdf.columns if pattern.match(c)]
    
    base_cols = ['TARGET_FID', 'ruianso_id', 'bobyosl21', 'sum_byt', 'zpvybu', 'kod', 'npodl']
    df = gdf[base_cols + np_cols].copy()
    df = df.drop_duplicates(subset=['TARGET_FID'])

    df['TARGET_FID'] = df['TARGET_FID'].astype(str)
    df['kod'] = df['kod'].apply(clean_code)
    df['sum_byt'] = df['sum_byt'].fillna(0).astype(int)
    df['bobyosl21'] = df['bobyosl21'].fillna(0).astype(int)
    df['npodl'] = pd.to_numeric(df['npodl'], errors='coerce').fillna(0).astype(int)
    df['zpvybu'] = df['zpvybu'].astype(str).str.zfill(2)

    def get_res_floors_smart(row):
        res_floors = [int(pattern.match(c).group(1)) for c in np_cols if str(row[c]).lower() == 'bydlení']
        if not res_floors and (row['bobyosl21'] > 0 or row['sum_byt'] > 0):
            if row['npodl'] > 0:
                res_floors = list(range(1, row['npodl'] + 1))
            else:
                res_floors = [1]
        return res_floors

    print("Generuji inteligentní seznam obytných pater...")
    df['res_floors'] = df.apply(get_res_floors_smart, axis=1)
    df = df[df['res_floors'].map(len) > 0].copy()
    return df

def assign_households_locally(df_hh, df_buildings):
    print("Phase 1: Hlavní ubytování (priorita: počet lidí > počet bytů)...")
    df_hh['assigned_TARGET_FID'] = None
    df_hh['assigned_floor'] = None
    df_hh['neighb_code'] = df_hh['neighb_code'].apply(clean_code)
    
    hh_dict = {}
    for idx, row in df_hh.iterrows():
        hh_dict.setdefault(row['neighb_code'], {}).setdefault(row['hh_building_type'], []).append(idx)
    
    hh_info = df_hh[['hh_size', 'building_floor', 'neighb_code']].to_dict('index')
    
    current_pop = {fid: 0 for fid in df_buildings['TARGET_FID']}
    current_units = {fid: 0 for fid in df_buildings['TARGET_FID']}
    
    all_mc = df_buildings['kod'].unique()
    
    for mc in all_mc:
        if mc not in hh_dict:
            continue
        mc_b = df_buildings[df_buildings['kod'] == mc]
        
        for h_type, b_code in [('rd','07'), ('ostatni_budovy','ostatni'), ('bd','06')]:
            if b_code == 'ostatni':
                b_sub = mc_b[~mc_b['zpvybu'].isin(['06','07'])]
            else:
                b_sub = mc_b[mc_b['zpvybu'] == b_code]
            
            for _, b in b_sub.iterrows():
                fid = b['TARGET_FID']
                target_pop = b['bobyosl21']
                max_units = b['sum_byt']
                res_floors = b['res_floors']
                
                while current_pop[fid] < target_pop:
                    candidates = hh_dict.get(mc, {}).get(h_type, [])
                    if not candidates:
                        all_candidates = [i for t in hh_dict.get(mc, {}).values() for i in t]
                        if not all_candidates:
                            break
                        candidates = all_candidates
                    
                    sample = random.sample(candidates, min(len(candidates), 500))
                    best_idx, min_score = None, float('inf')
                    for idx in sample:
                        hh_size = hh_info[idx]['hh_size']
                        hh_floor = hh_info[idx]['building_floor']
                        # Předáváme res_floors budovy do score_v3
                        score = score_v3(hh_size, hh_floor, current_pop[fid], target_pop, res_floors)
                        if score < min_score:
                            min_score, best_idx = score, idx
                    
                    if best_idx is None:
                        break
                    
                    df_hh.at[best_idx, 'assigned_TARGET_FID'] = fid
                    df_hh.at[best_idx, 'assigned_floor'] = get_best_floor(hh_info[best_idx]['building_floor'], res_floors)
                    current_pop[fid] += hh_info[best_idx]['hh_size']
                    current_units[fid] += 1
                    
                    for t in hh_dict[mc]:
                        if best_idx in hh_dict[mc][t]:
                            hh_dict[mc][t].remove(best_idx)
                            break
                    
                    if current_pop[fid] >= target_pop:
                        break
    return df_hh

def handle_leftovers_v3(df_hh, df_buildings):
    unassigned = df_hh[df_hh['assigned_TARGET_FID'].isna()].index
    if len(unassigned) == 0:
        return df_hh
    print(f"Phase 2: Řeším {len(unassigned)} přebytků (priorita: dobudování populace)...")
    
    assigned_df = df_hh[df_hh['assigned_TARGET_FID'].notna()]
    current_pop = assigned_df.groupby('assigned_TARGET_FID')['hh_size'].sum().to_dict()
    current_units = assigned_df.groupby('assigned_TARGET_FID').size().to_dict()
    
    b_info = df_buildings.set_index('TARGET_FID').to_dict('index')
    mc_map = {}
    for fid, d in b_info.items():
        mc_map.setdefault(d['kod'], []).append(fid)
    
    all_mc = list(mc_map.keys())
    
    for idx in unassigned:
        row = df_hh.loc[idx]
        mc = row['neighb_code']
        h_size = row['hh_size']
        h_floor_str = row['building_floor']
        
        if mc not in mc_map:
            continue
        
        fids = mc_map[mc]
        underpopulated = [f for f in fids if current_pop.get(f, 0) < b_info[f]['bobyosl21']]
        if underpopulated:
            fid = random.choice(underpopulated)
        elif any(current_units.get(f, 0) < b_info[f]['sum_byt'] for f in fids):
            fid = random.choice([f for f in fids if current_units.get(f, 0) < b_info[f]['sum_byt']])
        else:
            fid = random.choice(fids)
        
        df_hh.at[idx, 'assigned_TARGET_FID'] = fid
        df_hh.at[idx, 'assigned_floor'] = get_best_floor(h_floor_str, b_info[fid]['res_floors'])
        current_pop[fid] = current_pop.get(fid, 0) + h_size
        current_units[fid] = current_units.get(fid, 0) + 1
    return df_hh

def optimize_by_swapping_v2(df_hh, df_buildings, iterations=50000):
    print(f"Phase 3: Optimalizace ({iterations} iterací) – zlepšení shody populace...")
    valid_mask = df_hh['assigned_TARGET_FID'].notna()
    current_pop = df_hh[valid_mask].groupby('assigned_TARGET_FID')['hh_size'].sum().to_dict()
    target_pop = df_buildings.set_index('TARGET_FID')['bobyosl21'].to_dict()
    b_res_floors = df_buildings.set_index('TARGET_FID')['res_floors'].to_dict()
    mc_list = df_hh['neighb_code'].unique()
    
    for i in range(iterations):
        mc = random.choice(mc_list)
        mc_indices = df_hh[df_hh['neighb_code'] == mc].index
        if len(mc_indices) < 2:
            continue
        idx1, idx2 = random.sample(list(mc_indices), 2)
        fid1, fid2 = df_hh.at[idx1, 'assigned_TARGET_FID'], df_hh.at[idx2, 'assigned_TARGET_FID']
        if not fid1 or not fid2 or fid1 == fid2:
            continue
        s1, s2 = df_hh.at[idx1, 'hh_size'], df_hh.at[idx2, 'hh_size']
        err_before = (current_pop.get(fid1, 0) - target_pop.get(fid1, 0))**2 + \
                     (current_pop.get(fid2, 0) - target_pop.get(fid2, 0))**2
        new_p1, new_p2 = current_pop[fid1] - s1 + s2, current_pop[fid2] - s2 + s1
        err_after = (new_p1 - target_pop.get(fid1, 0))**2 + (new_p2 - target_pop.get(fid2, 0))**2
        if err_after < err_before:
            df_hh.at[idx1, 'assigned_TARGET_FID'], df_hh.at[idx2, 'assigned_TARGET_FID'] = fid2, fid1
            df_hh.at[idx1, 'assigned_floor'] = get_best_floor(df_hh.at[idx1, 'building_floor'], b_res_floors[fid2])
            df_hh.at[idx2, 'assigned_floor'] = get_best_floor(df_hh.at[idx2, 'building_floor'], b_res_floors[fid1])
            current_pop[fid1], current_pop[fid2] = new_p1, new_p2
        if i % 10000 == 0:
            print(f"   ... iterace {i}")
    return df_hh

# --- SPUŠTĚNÍ ---
os.makedirs("output/spatial", exist_ok=True)
df_hh = pd.read_pickle("output/synthetic_population/with_households/households/synth_households_DHWZ_v5.pkl")
df_hh = split_household_building_floor(df_hh)
df_b = extract_building_table("hello.gpkg")

df_hh = assign_households_locally(df_hh, df_b)
df_hh = handle_leftovers_v3(df_hh, df_b)
df_hh = optimize_by_swapping_v2(df_hh, df_b, iterations=100000)

# FINÁLNÍ PROPOJENÍ
print("Připravuji finální export...")
df_final = df_hh.merge(df_b[['TARGET_FID', 'ruianso_id']], left_on='assigned_TARGET_FID', right_on='TARGET_FID', how='left')

stats_p = df_hh.groupby('assigned_TARGET_FID')['hh_size'].sum()
stats_h = df_hh.groupby('assigned_TARGET_FID').size()
log = df_b[['TARGET_FID', 'ruianso_id', 'kod', 'bobyosl21', 'sum_byt']].copy().set_index('TARGET_FID')
log['real_p'], log['real_h'] = stats_p, stats_h
log = log.fillna(0)
log['diff_p'], log['diff_u'] = log['real_p'] - log['bobyosl21'], log['real_h'] - log['sum_byt']

df_final.to_csv("output/spatial/final_spatial.csv", sep=';', index=False, encoding='utf-8-sig')
log.to_csv("output/spatial/occupancy_log.csv", sep=';', encoding='utf-8-sig')

print(f"\nHotovo. Úspěšnost: {df_hh['assigned_TARGET_FID'].notna().sum()/len(df_hh)*100:.2f}%")