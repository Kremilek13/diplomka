import pandas as pd

# Nastavení cest k souborům
vstupni_csv = r'C:\Users\Eliska\Documents\takuzkonecne\diplomka\output\synthetic_population\individuals\synth_pop_DHWZ_v24.csv'
vystupni_pickle = r'C:\Users\Eliska\Documents\takuzkonecne\diplomka\output\synthetic_population\individuals\synth_pop_DHWZ_v24.pkl'

# Načtení CSV (sep=';' řeší tvůj požadavek na středník)
df = pd.read_csv(vstupni_csv, sep=';')

# Uložení do Pickle
df.to_pickle(vystupni_pickle)

print(f"Hotovo! Soubor byl uložen jako {vystupni_pickle}")