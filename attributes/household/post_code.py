import os

import pandas as pd

from attributes.marginal_data_reader import neighborhood_codes


def read_pc6_data() -> pd.DataFrame:
    """
    https://www.cbs.nl/nl-nl/maatwerk/2019/42/buurt-wijk-en-gemeente-2019-voor-postcode-huisnummer
    Returns:

    """
    path = os.path.join(
            os.path.dirname(__file__),
            '../../datasources/household/postal_code/pc6hnr20190801_gwb.csv')
    df = pd.read_csv(path, sep=';')
    df.loc[:, 'neighb_code'] = df.Buurt2019.map(lambda x: f'BU{x:08d}')
    df = df[df.neighb_code.isin(neighborhood_codes)]
    df = df.groupby(['neighb_code', 'PC6'])['Huisnummer'].count()
    df = df.reset_index().rename(columns={'Huisnummer': 'count'})

    return df
