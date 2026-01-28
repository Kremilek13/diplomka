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


def code_list_education(df) -> pd.DataFrame:
    codebook_path = os.path.join(
        os.path.dirname(__file__),
        '../datasources/code_lists/vzdelani.csv'
    )
    df_codes = pd.read_csv(codebook_path, sep=";", encoding="utf-8")
    df_codes.columns = df_codes.columns.str.strip().str.lower()
    if 'kód' not in df_codes.columns or 'text' not in df_codes.columns:
        raise ValueError(f"Číselník musí obsahovat sloupce 'kód' a 'text'. Nalezeno: {df_codes.columns.tolist()}")
    mapping = dict(zip(df_codes['kód'], df_codes['text']))
    df["education"] = df["education"].map(mapping)

    if df["education"].isna().any():
        print("POZOR: Některé kódy vzdělání se nepodařilo přeložit!")
        print(df[df["education"].isna()])
    return df


def code_list_economical_activity(df) -> pd.DataFrame:
    codebook_path = os.path.join(
        os.path.dirname(__file__),
        '../datasources/code_lists/ekonomicka_aktivita.csv'
    )
    df_codes = pd.read_csv(codebook_path, sep=";", encoding="utf-8")
    df_codes.columns = df_codes.columns.str.strip().str.lower()
    if 'kód' not in df_codes.columns or 'text' not in df_codes.columns:
        raise ValueError(f"Číselník musí obsahovat sloupce 'kód' a 'text'. Nalezeno: {df_codes.columns.tolist()}")
    mapping = dict(zip(df_codes['kód'], df_codes['text']))
    df["economical_activity"] = df["economical_activity"].map(mapping)

    if df["economical_activity"].isna().any():
        print("POZOR: Některé kódy ekonomické aktivity se nepodařilo přeložit!")
        print(df[df["economical_activity"].isna()])
    return df

