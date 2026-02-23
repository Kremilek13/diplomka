import os
import pandas as pd

def code_list_gender(df) -> pd.DataFrame:
    gender_map = {
        1: "male",
        2: "female",
    }

    df["gender"] = df["gender"].map(gender_map)

    if df["gender"].isna().any():
        print("POZOR: Některé kódy pohlaví se nepodařilo přeložit!")
        print(df[df["gender"].isna()])
    return df


def code_list_age_group(df) -> pd.DataFrame:
    age_group_map = {
        1: "0-14",
        2: "15-24",
        3: "25-44",
        4: "45-64",
        5: "64+"
    }

    df["age_group"] = df["age_group"].map(age_group_map)

    if df["age_group"].isna().any():
        print("POZOR: Některé kódy věkových skupin se nepodařilo přeložit!")
        print(df[df["age_group"].isna()])
    return df


def code_list_education(df, column) -> pd.DataFrame:
    '''df for translation; column: 'kategorie' for general category, 'text' for specific category'''
    codebook_path = os.path.join(
        os.path.dirname(__file__),
        '../datasources/code_lists/vzdelani.csv'
    )
    df_codes = pd.read_csv(codebook_path, sep=";", encoding="utf-8")
    df_codes.columns = df_codes.columns.str.strip().str.lower()
    if 'kód' not in df_codes.columns or column not in df_codes.columns:
        raise ValueError(f"Číselník musí obsahovat sloupce 'kód' a '{column}'. Nalezeno: {df_codes.columns.tolist()}")
    mapping = dict(zip(df_codes['kód'], df_codes[column]))
    df['education'] = df['education'].map(mapping)

    if df['education'].isna().any():
        print(f"POZOR: Některé kódy {column} se nepodařilo přeložit!")
        print(df[df['education'].isna()])
    return df


def code_list_economical_activity(df) -> pd.DataFrame:
    codebook_path = os.path.join(
        os.path.dirname(__file__),
        '../datasources/code_lists/ekonomicka_aktivita.csv'
    )
    df_codes = pd.read_csv(codebook_path, sep=";", encoding="utf-8")
    df_codes.columns = df_codes.columns.str.strip().str.lower()
    if 'kód' not in df_codes.columns or 'kategorie' not in df_codes.columns:
        raise ValueError(f"Číselník musí obsahovat sloupce 'kód' a 'kategorie'. Nalezeno: {df_codes.columns.tolist()}")
    mapping = dict(zip(df_codes['kód'], df_codes['kategorie']))
    df["economical_activity"] = df["economical_activity"].map(mapping)

    if df["economical_activity"].isna().any():
        print("POZOR: Některé kódy ekonomické aktivity se nepodařilo přeložit!")
        print(df[df["economical_activity"].isna()])
    return df

def code_list_place_activity(df) -> pd.DataFrame:
    codebook_path = os.path.join(
        os.path.dirname(__file__),
        '../datasources/code_lists/vyjizdka_misto.csv'
    )
    df_codes = pd.read_csv(codebook_path, sep=";", encoding="utf-8")
    df_codes.columns = df_codes.columns.str.strip().str.lower()
    if 'kód' not in df_codes.columns or 'kategorie' not in df_codes.columns:
        raise ValueError(f"Číselník musí obsahovat sloupce 'kód' a 'kategorie'. Nalezeno: {df_codes.columns.tolist()}")
    mapping = dict(zip(df_codes['kód'], df_codes['kategorie']))
    df["place_activity"] = df["place_activity"].map(mapping)

    if df["place_activity"].isna().any():
        print("POZOR: Některé kódy místa aktivity se nepodařilo přeložit!")
        print(df[df["place_activity"].isna()])
    return df

def create_dictionary() -> dict:
    '''Create a dictionary from code list dataframe table (for specific to general education mapping)'''
    codebook_path = os.path.join(
        os.path.dirname(__file__),
        '../datasources/code_lists/vzdelani.csv'
    )
    df_codes = pd.read_csv(codebook_path, sep=";", encoding="utf-8")
    df_codes['text'] = df_codes['text'].str.strip()
    df_codes['kategorie'] = df_codes['kategorie'].str.strip()
    mapping_dict = dict(zip(df_codes['text'], df_codes['kategorie']))

    return mapping_dict
