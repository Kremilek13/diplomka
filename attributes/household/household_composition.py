import os

import pandas as pd


def read_couples_age_disparity():
    """
    Manually downloaded from https://www.cbs.nl/en-gb/news/2019/07/groom-usually-older-than-bride
    Returns:

    """
    data_path = os.path.join(
            os.path.dirname(__file__),
            "../../datasources/household/household_composition/table_7ab235bf-b5a7-4077-bf56-3f5c8efec7d0.csv"
    )
    df = pd.read_csv(data_path, sep=',')
    df.loc[:, 'male_female_age_gap'] = [
        '0-0', '', '-1-4', '-5-9', '-10-14', '-15-19', '-20-100', '', '1-4', '5-9', '10-14', '15-19', '20-100'
    ]
    df = df.set_index('male_female_age_gap').drop('')['All marriages (%)']
    df /= 100
    df.name = 'count'
    return df


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
            "../../datasources/household/household_composition/Geboorte__kerncijfers_per_regio_25052024_182014.csv"
    )
    df = pd.read_csv(data_path, sep=';')
    df.columns = df.columns.str.replace(r'Levend geboren kinderen: leeftijd moe.../(.*) \(aantal\)', r'\1', regex=True)
    df.columns = df.columns.str.replace('Levend geboren kinderen: rangnummer/(\d)e.*', ' ', regex=True)
    df.drop(['Perioden', "Regio's", " "], axis=1, inplace=True)
    df.columns = df.columns.str.replace(r'(\d+) tot (\d+) jaar', r'\1-\2', regex=True)
    df.columns = df.columns.str.replace('45 jaar of ouder', '45-200').str.replace('Jonger dan 20 jaar', '14-20')
    df = df.T
    df = df / df.sum()
    df.columns = ['fraction']
    df.index.name = 'age_difference'

    return df['fraction']
