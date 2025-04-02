import os
from typing import Literal

import pandas as pd
from ipfn import ipfn

from gensynthpop.evaluation.validation import validate_fitted_distribution
from gensynthpop.utils.extractors import synthetic_population_to_contingency


def read_vehicle_ownership() -> pd.DataFrame:
    """
    https://opendata.cbs.nl/statline/#/CBS/nl/dataset/81845NED/table?dl=A7D91

    Download CSV without statistical symbols (zonder statistische symbolen)

    Perioden: 2015*
    Row Variables:
        - Huishoudenkenmerken:
            - Huishoudenssamenstellig:
                - Type: Eenpersoonshuishouden
                - Type: Eenoudergezin
                - Type: Paar, met kind(eren)
                - Type: Paar, zonder kinderen
            - Aantal personen in huishouden
                - Huishoudensgroote: 1 persoon
                - Huishoudensgroote: 2 personen
                - Huishoudensgroote: 3 personen
                - Huishoudensgroote: 4 personen
                - Huishoudensgroote: 5 of meer personen
            - Gestandardiseerd inkomen 20% groepen:
                - Gestandaardiseerd inkomen: 1e 20%-groep
                - Gestandaardiseerd inkomen: 2e 20%-groep
                - Gestandaardiseerd inkomen: 3e 20%-groep
                - Gestandaardiseerd inkomen: 4e 20%-groep
                - Gestandaardiseerd inkomen: 5e 20%-groep
        - Aantal voertuigen in huishouden
            - Minimaal één voertuig
            - Eén voortuig
            - Twee voertuigen
            - Drie of meer voertuigen

    Column Variables:
        - Huishoudens in bezit van auto
            - Huishoudens in bezit van auto
            - % Huishoudens in bezit van auto
        - Huishoudens in bezit van motor
            - Huishoudens in bezit van motor
            - % Huishoudens in bezit van motor

    Returns:

    """
    data_path = os.path.join(
            os.path.dirname(__file__),
            "../../datasources/household/vehicle_ownership/Huishoudens_met_auto_of_motor__2010_2015_14062024_171657.csv"
    )
    df = pd.read_csv(data_path, sep=';').drop('Perioden', axis=1)
    df.rename(columns={
        'Aantal voertuigen in huishouden': 'n_vehicles',
        'Huishoudens in bezit van auto/Huishoudens in bezit van auto (aantal)': 'car',
        'Huishoudens in bezit van auto/% Huishoudens in bezit van auto  (%)': 'car_relative',
        'Huishoudens in bezit van motor/Huishoudens in bezit van motor (aantal)': 'motorcycle',
        'Huishoudens in bezit van motor/% Huishoudens in bezit van motor  (%)': 'motorcycle_relative'
    }, inplace=True)

    df.replace({
        'Minimaal één voertuig': 0, 'Eén voertuig': 1, 'Twee voertuigen': 2,
        'Drie of meer voertuigen': 3,
        'Type: Eenpersoonshuishouden': 'single',
        'Type: Eenoudergezin': 'single_parent',
        'Type: Paar, zonder kind': 'couple_no_children',
        'Type: Paar, met kind(eren)': 'couple_with_children',
        'Huishoudensgrootte: 1 persoon': '1-person',
        'Huishoudensgrootte: 2 personen': '2-person',
        'Huishoudensgrootte: 3 personen': '3-person',
        'Huishoudensgrootte: 4 personen': '4-person',
        'Huishoudensgrootte: 5 of meer personen': '5-person',
        'Gestandaardiseerd inkomen: 1e 20%-groep': 'income-group-1',
        'Gestandaardiseerd inkomen: 2e 20%-groep': 'income-group-2',
        'Gestandaardiseerd inkomen: 3e 20%-groep': 'income-group-3',
        'Gestandaardiseerd inkomen: 4e 20%-groep': 'income-group-4',
        'Gestandaardiseerd inkomen: 5e 20%-groep': 'income-group-5',
    }, inplace=True)

    df = df.astype({'car': float, 'motorcycle': float})
    df.loc[:, 'car_relative_float'] = df.car_relative.map(lambda x: float(x.replace(',', '.')))
    df.loc[:, 'motorcycle_relative_float'] = df.motorcycle_relative.map(lambda x: float(x.replace(',', '.')))
    msk_no_vehicles = df.n_vehicles == 0
    df.loc[msk_no_vehicles, 'car'] = df.loc[msk_no_vehicles].car / df.loc[msk_no_vehicles].car_relative_float * 100
    df.loc[msk_no_vehicles, 'motorcycle'] = df.loc[msk_no_vehicles].motorcycle / df.loc[
        msk_no_vehicles].motorcycle_relative_float * 100

    df.drop(['car_relative', 'motorcycle_relative', 'car_relative_float', 'motorcycle_relative_float'], axis=1,
            inplace=True)

    return df


def get_vehicle_ownership_for_type(vehicle_type: Literal['car', 'motorcycle'],
                                   max_licenses_per_household: int) -> pd.DataFrame:
    """
    Attempts to estimate the joint distribution of number of household owned vehicles from
    household type, household size and income group.

    Adds a constraint column for the number of licenses of the vehicle type owned by the household members must be
    at least as big as the number of vehicles owned.

    Data set can be obtained for `car` and `motor` vehicles separately
    Args:
        vehicle_type:
        max_licenses_per_household

    Returns:

    """
    df = read_vehicle_ownership()
    df_margins_hh_type = df.loc[df.Huishoudkenmerken.isin(
            ['single', 'single_parent', 'couple_no_children', 'couple_with_children']
    ), ['n_vehicles', 'Huishoudkenmerken', vehicle_type]].rename(
            columns={'Huishoudkenmerken': 'income_household_type'}).set_index(['income_household_type', 'n_vehicles'])

    df_margins_hh_size = df.loc[df.Huishoudkenmerken.isin(
            ['1-person', '2-person', '3-person', '4-person', '5-person', ]
    ), ['n_vehicles', 'Huishoudkenmerken', vehicle_type]].rename(
            columns={'Huishoudkenmerken': 'hh_size'}).set_index(['hh_size', 'n_vehicles'])

    df_margins_income_group = df.loc[df.Huishoudkenmerken.isin(
            ['income-group-1', 'income-group-2', 'income-group-3', 'income-group-4', 'income-group-5']
    ), ['n_vehicles', 'Huishoudkenmerken', vehicle_type]].rename(
            columns={'Huishoudkenmerken': 'income_group'}).set_index(['income_group', 'n_vehicles'])

    df_joint = df_margins_hh_size.groupby(level=0).first().reset_index()[["hh_size"]].merge(
            df_margins_hh_type.groupby(level=0).first().reset_index().income_household_type, how='cross'
    ).merge(
            df_margins_income_group.groupby(level=0).first().reset_index().income_group, how='cross'
    ).merge(
            df_margins_hh_type.groupby(level=1).first().reset_index().n_vehicles, how='cross'
    ).merge(
            df_margins_hh_type, how='left', left_on=['income_household_type', 'n_vehicles'], right_index=True
    ).merge(pd.Series(range(max_licenses_per_household + 1), name=f'{vehicle_type}_license'), how='cross')
    df_joint.loc[df_joint[f'{vehicle_type}_license'] < df_joint.n_vehicles, vehicle_type] = 0

    df_joint = ipfn.ipfn(
            df_joint,
            [
                df_margins_hh_type[vehicle_type],
                df_margins_income_group[vehicle_type],
                df_margins_hh_size[vehicle_type],
                df_margins_hh_type.groupby(level=0)[vehicle_type].sum(),
                df_margins_income_group.groupby(level=0)[vehicle_type].sum(),
                df_margins_hh_size.groupby(level=0)[vehicle_type].sum(),
            ], [
                ['income_household_type', 'n_vehicles'],
                ['income_group', 'n_vehicles'],
                ['hh_size', 'n_vehicles'],
                ['income_household_type'],
                ['income_group'],
                ['hh_size']
            ],
            vehicle_type
    ).iteration()

    df_joint.replace({f'{i}-person': i for i in range(0, 6)}, inplace=True)
    df_joint.replace({f'income-group-{i}': i for i in range(1, 6)}, inplace=True)

    return df_joint.rename(columns={vehicle_type: 'count', 'income_group': 'vehicle_ownership_income_group'})


def fit_vehicle_ownership_for_type(df_synth_households: pd.DataFrame,
                                   vehicle_type: Literal['car', 'motorcycle'],
                                   max_licenses_per_household: int) -> pd.DataFrame:
    df_contingency = get_vehicle_ownership_for_type(vehicle_type, max_licenses_per_household)

    # Avoid a weird bug where if you use a tuple with the last element being a numpy int object (e.g, int32, int64) with
    # the value 1, numpy things it should be interpreted as a type. Does not occur with floats.
    df_contingency = df_contingency.astype(
            {
                'hh_size': 'float', 'vehicle_ownership_income_group': 'float', 'n_vehicles': 'float',
                f'{vehicle_type}_license': 'float'
            })

    dimensions = get_vehicle_ownership_dimensions(vehicle_type)

    margins = [
        synthetic_population_to_contingency(df_synth_households, dm, len(dm) > 1)['count']
        for dm in dimensions
    ]

    df_fitted = ipfn.ipfn(
            df_contingency,
            margins,
            dimensions,
            'count'
    ).iteration()

    for dm, margin in zip(dimensions, margins):
        validate_fitted_distribution(
                df_fitted,
                margin, dm, vehicle_type
        )

    return df_fitted


def get_vehicle_ownership_dimensions(vehicle_type: Literal['car', 'motorcycle']):
    return [
        # Single
        ['income_household_type'], ['hh_size'], ['vehicle_ownership_income_group'], [f'{vehicle_type}_license'],
        # Double
        ['income_household_type', 'hh_size'], ['income_household_type', 'vehicle_ownership_income_group'],
        ['income_household_type', f'{vehicle_type}_license'],
        ['hh_size', 'vehicle_ownership_income_group'], ['hh_size', f'{vehicle_type}_license'],
        ['vehicle_ownership_income_group', f'{vehicle_type}_license'],
        # Triple
        ['income_household_type', 'hh_size', 'vehicle_ownership_income_group'],
        ['income_household_type', 'hh_size', f'{vehicle_type}_license'],
        ['income_household_type', 'vehicle_ownership_income_group', f'{vehicle_type}_license'],
        ['hh_size', 'vehicle_ownership_income_group', f'{vehicle_type}_license'],
        # All
        ['income_household_type', 'hh_size', 'vehicle_ownership_income_group', f'{vehicle_type}_license'],
    ]
