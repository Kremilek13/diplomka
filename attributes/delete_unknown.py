import pandas as pd
import numpy as np

def replace_value(df: pd.DataFrame, 
                  target_column: str, 
                  value_name: str, 
                  conditioning_columns: list) -> pd.DataFrame:
    global_valid = df.loc[df[target_column] != value_name, target_column]
    global_probs = global_valid.value_counts(normalize=True)
    
    # 1. Definujeme funkci, která se provede pro každou skupinu (např. pro "Muže 20-25 let")
    def impute_group(group):
        # Najdeme, kdo v této skupině má "nezjištěno"
        is_undefined = group[target_column] == value_name
        
        # Pokud ve skupině nikdo takový není, vrátíme ji beze změny
        if not is_undefined.any():
            return group
            
        # Získáme hodnoty těch, co JSOU zjištění (to je ten váš "most probable" základ)
        valid_values = group.loc[~is_undefined, target_column]
        
        if valid_values.empty:
            # Skupina nemá žádné platné hodnoty. Místo "return group" 
            # použijeme náš celoměstský záložní plán (global_probs).
            if global_probs.empty:
                # Tohle by nastalo jen kdyby v CELÉ tabulce bylo "nezjištěno".
                return group 
            probs = global_probs
        else:
            # Normální stav: skupina má z čeho brát
            probs = valid_values.value_counts(normalize=True)
        # ==========================
        
        new_values = np.random.choice(probs.index, size=is_undefined.sum(), p=probs.values)
        group.loc[is_undefined, target_column] = new_values
        return group

    # 2. Hlavní magie: Pandas rozdělí data podle sloupců (conditioning_columns),
    # aplikuje naši funkci a zase to složí dohromady.
    print(f"Nahrazuji '{value_name}' ve sloupci '{target_column}'...")
    return df.groupby(conditioning_columns, group_keys=False).apply(impute_group)
