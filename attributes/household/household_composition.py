import os

import pandas as pd


def read_couples_age_disparity():
    """
    Manually downloaded from https://www.cbs.nl/en-gb/news/2019/07/groom-usually-older-than-bride
    Returns:

    """
    data_path = os.path.join(
            os.path.dirname(__file__),
            "../../datasources/household/household_composition/Snatky_rozdil_veku.csv"
    )
    df = pd.read_csv(data_path, sep=',')
    def age_gap(row):
        pohlavi = row['POHLAVI_STARSIHO_SNOUBENCE']
        rozdil = str(row['ROZDIL_VEKU_SNOUBENCU'])
        rozdil = str(row['ROZDIL_VEKU_SNOUBENCU']).replace('_', '-')
        if rozdil == '20avetsi':
            rozdil = '20-100'
        if pohlavi == 'MZ':
            return '0-0'
        elif pohlavi == 'Z':
            # Žena starší -> přidáme mínus (-10-14)
            return '-' + rozdil
        else:
            # Muž starší (M) -> necháme tak (10-14)
            return rozdil

    df['male_female_age_gap'] = df.apply(age_gap, axis=1)
    df_grouped = df.groupby('male_female_age_gap')['POCET_SNATKU'].sum()
    total_count = df_grouped.sum()
    if total_count > 0:
        df_grouped = df_grouped / total_count
    
    df_grouped.name = 'count'
    print(df_grouped)
    
    return df_grouped


def read_couples_gender_disparity():
    """
    https://opendata.cbs.nl/#/CBS/en/dataset/37772eng/table?dl=A68BB

    Periods: 2019

    Row Variables:
        - Marriages
            - Between man and woman
            - Between men
            - Between women
        - Partnership registrations
            - Total partnership registrations
                - Between man and woman
                - Between men
                - Between women

    Returns:

    """
    data_path = os.path.join(
            os.path.dirname(__file__),
            "../../datasources/household/household_composition/Marriages__key_figures_25052024_182843.csv"
    )
    df = pd.read_csv(data_path, sep=';').drop('Periods', axis=1).T
    df.loc[:, ['first_partner', 'second_partner']] = [None, None]
    df.iloc[[0, 3], [1, 2]] = ['male', 'female']
    df.iloc[[1, 4], [1, 2]] = ['male', 'male']
    df.iloc[[2, 5], [1, 2]] = ['female', 'female']
    df = df.groupby(['first_partner', 'second_partner']).sum().transform(lambda x: x / x.sum())

    df.rename(columns={0: 'count'}, inplace=True)
    return df['count']


def get_mother_age_disparity():
    """
    https://opendata.cbs.nl/#/CBS/nl/dataset/37201/table?dl=A68B5

    Regio's: 's-Gravenhage (gemeente)
    Perioden: 2019

    Row Variables:
        - Onderwerpen:
            Levend geboren kinderen: leeftijd moe...
                Jonger dan 20 jaar
                    20 tot 25 jaar
                    25 tot 30 jaar
                    30 tot 35 jaar
                    35 tot 40 jaar
                    40 tot 45 jaar
                    45 jaar of ouder
                Levend geboren kinderen: rangnummer
                    1e kind
                    2e kind
                    3e kind
                    4e of volgende kinderen

    Returns:

    """
    data_path = os.path.join(
            os.path.dirname(__file__),
            "../../datasources/household/household_composition/Narozeni_2021_podle_veku.csv"
    )
    df = pd.read_csv(data_path, sep=',')

    df = df[['MATKA_VEK', 'ZIVE_NAROZENI']].copy()
    df['age_difference'] = df['MATKA_VEK'].astype(str).str.replace('_', '-')
    df = df.set_index('age_difference')
    total_births = df['ZIVE_NAROZENI'].sum()
    df['fraction'] = df['ZIVE_NAROZENI'] / total_births
    
    return df['fraction']
