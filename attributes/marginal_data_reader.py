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
                                '../datasources/marginal/marginal_casti_brna.csv')
    df_marginal = pd.read_csv(margins_path, sep=";")
    column_names = [original for original, renamed in marginal_data_code_map.items() if renamed in columns]
    if 'Kód městské části' not in column_names:
        column_names.append('Kód městské části')
    df_marginal = df_marginal[column_names]
    df_marginal = df_marginal.rename(columns=marginal_data_code_map)
    df_marginal = df_marginal[df_marginal.kód.isin(neighborhood_codes)]
    print(df_marginal)
    if len(columns) > 1:
        return multicolumn_to_attribute_values(df_marginal, attribute_name, columns)
    else:
        return df_marginal.set_index('kód')


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
        [582786, 551082, 551325, 551198, 551066, 551317, 551376, 551406, 551074, 551171, 551210, 551147, 551228, 551007, 551287, 551252, 551236, 551112, 551422, 551244, 551031, 551295, 551091, 550973, 551309, 551431, 551279, 550990, 551368, 551058
        ], name="kód")




age_groups = ['0-15', '15-25', '25-45', '45-65', '65+']

# Defines how the column names used by CBS map to more convenient names we can use later.
# May have to be extended if more marginal attributes are used
marginal_data_code_map = {
    'Kód městské části': 'kód',
    'celkem': 'populace',
    'muži': 'muži',
    'ženy': 'ženy',
    # 'k_0Tot15Jaar_8': '0-15',
    # 'k_15Tot25Jaar_9': '15-25',
    # 'k_25Tot45Jaar_10': '25-45',
    # 'k_45Tot65Jaar_11': '45-65',
    # 'k_65JaarOfOuder_12': '65+',
    # 'Ongehuwd_13': 'unmarried',
    # 'Gehuwd_14': 'maried',
    # 'WestersTotaal_17': 'Western',
    # 'NietWestersTotaal_18': 'NonWestern',
    # 'OpleidingsniveauLaag_64': 'education_absolved_low',
    # 'OpleidingsniveauMiddelbaar_65': 'education_absolved_middle',
    # 'OpleidingsniveauHoog_66': 'education_absolved_high',
    # 'HuishoudensTotaal_28': 'households',
    # 'Eenpersoonshuishoudens_29': 'single_person',
    # 'HuishoudensZonderKinderen_30': 'without_children',
    # 'HuishoudensMetKinderen_31': 'with_children'
}
