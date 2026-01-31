import pandas as pd
import numpy as np

def replace_value(df: pd.DataFrame, 
                  target_column: str, 
                  value_name: str, 
                  conditioning_columns: list) -> pd.DataFrame:
    
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
            return group # Nemáme se od koho učit
            
        # Spočítáme pravděpodobnosti (např. ZŠ=10%, SŠ=50%, VŠ=40%)
        probs = valid_values.value_counts(normalize=True)
        
        # Vygenerujeme nové hodnoty pro ty "nezjištěné"
        # np.random.choice hází kostkou podle vah (probs)
        new_values = np.random.choice(probs.index, size=is_undefined.sum(), p=probs.values)
        
        # Zapíšeme je zpátky
        group.loc[is_undefined, target_column] = new_values
        return group

    # 2. Hlavní magie: Pandas rozdělí data podle sloupců (conditioning_columns),
    # aplikuje naši funkci a zase to složí dohromady.
    print(f"Nahrazuji '{value_name}' ve sloupci '{target_column}'...")
    return df.groupby(conditioning_columns, group_keys=False).apply(impute_group)
