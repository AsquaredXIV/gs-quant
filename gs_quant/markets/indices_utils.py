"""
Copyright 2019 Goldman Sachs.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

import datetime as dt
import pandas as pd

from enum import Enum
from functools import partial
from pydash import get
from time import sleep
from typing import Dict, List, Optional, Union

from gs_quant.api.gs.assets import AssetClass, GsAssetApi
from gs_quant.api.gs.data import GsDataApi
from gs_quant.api.gs.monitors import GsMonitorsApi
from gs_quant.api.utils import ThreadPoolManager
from gs_quant.base import EnumBase
from gs_quant.datetime.date import prev_business_date
from gs_quant.session import GsSession
from gs_quant.target.data import DataQuery


class BasketType(EnumBase, Enum):
    """ Basket Types """
    CUSTOM_BASKET = 'Custom Basket'
    RESEARCH_BASKET = 'Research Basket'

    def __repr__(self):
        return self.value

    @classmethod
    def to_list(cls):
        return [basket_type.value for basket_type in cls]


class CorporateActionType(EnumBase, Enum):
    """ Different types of corporate actions """
    ACQUISITION = 'Acquisition'
    CASH_DIVIDEND = 'Cash Dividend'
    IDENTIFIER_CHANGE = 'Identifier Change'
    RIGHTS_ISSUE = 'Rights Issue'
    SHARE_CHANGE = 'Share Change'
    SPECIAL_DIVIDEND = 'Special Dividend'
    SPIN_OFF = 'Spin Off'
    STOCK_DIVIDEND = 'Stock Dividend'
    STOCK_SPLIT = 'Stock Split'

    def __repr__(self):
        return self.value

    @classmethod
    def to_list(cls):
        return [ca_type.value for ca_type in cls]


class CustomBasketStyles(EnumBase, Enum):
    """ Styles for Custom Baskets """
    AD_HOC_DESK_WORK = 'Ad Hoc Desk Work'
    CLIENT_CONSTRUCTED_WRAPPER = 'Client Constructed/Wrapper'
    CONSUMER = 'Consumer'
    ENERGY = 'Energy'
    ENHANCED_INDEX_SOLUTIONS = 'Enhanced Index Solutions'
    ESG = 'ESG'
    FACTORS = 'Factors'
    FINANCIALS = 'Financials'
    FLAGSHIP = 'Flagship'
    GEOGRAPHIC = 'Geographic'
    GROWTH = 'Growth'
    HEALTHCARE = 'Health Care'
    HEDGING = 'Hedging'
    INDUSTRIALS = 'Industrials'
    MATERIALS = 'Materials'
    MOMENTUM = 'Momentum'
    PIPG = 'PIPG'
    SECTORS_INDUSTRIES = 'Sectors/Industries'
    SIZE = 'Size'
    STRUCTURED_ONE_DELTA = 'Structured One Delta'
    THEMATIC = 'Thematic'
    TMT = 'TMT'
    UTILITIES = 'Utilities'
    VALUE = 'Value'
    VOLATILITY = 'Volatility'

    def __repr__(self):
        return self.value


class IndicesDatasets(EnumBase, Enum):
    """ Indices Datasets """
    BASKET_FUNDAMENTALS = 'BASKET_FUNDAMENTALS'
    COMPOSITE_THEMATIC_BETAS = 'COMPOSITE_THEMATIC_BETAS'
    CORPORATE_ACTIONS = 'CA'
    GIRBASKETCONSTITUENTS = 'GIRBASKETCONSTITUENTS'
    GSBASKETCONSTITUENTS = 'GSBASKETCONSTITUENTS'
    GSCB_FLAGSHIP = 'GSCB_FLAGSHIP'
    STS_FUNDAMENTALS = 'STS_FUNDAMENTALS'
    STS_INDICATIVE_LEVELS = 'STS_INDICATIVE_LEVELS'

    def __repr__(self):
        return self.value


class PriceType(EnumBase, Enum):
    """ Index Price Types """
    INDICATIVE_CLOSE_PRICE = 'indicativeClosePrice'
    OFFICIAL_CLOSE_PRICE = 'officialClosePrice'

    def __repr__(self):
        return self.value

    @classmethod
    def to_list(cls):
        return [price_type for price_type in cls]


class Region(EnumBase, Enum):
    """ Region of the index """
    AMERICAS = 'Americas'
    ASIA = 'Asia'
    EM = 'EM'
    EUROPE = 'Europe'
    GLOBAL = 'Global'

    def __repr__(self):
        return self.value


class ResearchBasketStyles(EnumBase, Enum):
    """ Styles for Research Baskets """
    ASIA_EX_JAPAN = 'Asia ex-Japan'
    EQUITY_THEMATIC = 'Equity Thematic'
    EUROPE = 'Europe'
    FUND_OWNERSHIP = 'Fund Ownership'
    FUNDAMENTALS = 'Fundamentals'
    FX_OIL = 'FX/Oil'
    GEOGRAPHICAL_EXPOSURE = 'Geographical Exposure'
    HEDGE_FUND = 'Hedge Fund'
    IP_FACTORS = 'Investment Profile (IP) Factors'
    JAPAN = 'Japan'
    MACRO = 'Macro'
    MACRO_SLICE_STYLES = 'Macro Slice/Styles'
    MUTUAL_FUND = 'Mutual Fund'
    POSITIONING = 'Positioning'
    PORTFOLIO_STRATEGY = 'Portfolio Strategy'
    RISK_AND_LIQUIDITY = 'Risk & Liquidity'
    SECTOR = 'Sector'
    SHAREHOLDER_RETURN = 'Shareholder Return'
    STYLE_FACTOR_AND_FUNDAMENTAL = 'Style, Factor and Fundamental'
    STYLES_THEMES = 'Style/Themes'
    TACTICAL_RESEARCH = 'Tactical Research'
    THEMATIC = 'Thematic'
    US = 'US'
    WAVEFRONT_COMPONENTS = 'Wavefront Components'
    WAVEFRONT_PAIRS = 'Wavefront Pairs'
    WAVEFRONTS = 'Wavefronts'

    def __repr__(self):
        return self.value


class ReturnType(EnumBase, Enum):
    """ Determines the index calculation methodology with respect to dividend reinvestment """
    GROSS_RETURN = 'Gross Return'
    PRICE_RETURN = 'Price Return'
    TOTAL_RETURN = 'Total Return'

    def __repr__(self):
        return self.value


class STSIndexType(EnumBase, Enum):
    """ STS Types """

    ACCESS = 'Access'
    MULTI_ASSET_ALLOCATION = 'Multi-Asset Allocation'
    RISK_PREMIA = 'Risk Premia'
    SYSTEMATIC_HEDGING = 'Systematic Hedging'

    def __repr__(self):
        return self.value

    @classmethod
    def to_list(cls):
        return [sts_type.value for sts_type in cls]


class WeightingStrategy(EnumBase, Enum):
    """ Strategy used to price the index's position set """
    EQUAL = 'Equal'
    MARKET_CAPITALIZATION = 'Market Capitalization'
    QUANTITY = 'Quantity'
    WEIGHT = 'Weight'

    def __repr__(self):
        return self.value


def get_my_baskets(user_id: str = None) -> Optional[pd.DataFrame]:
    """
    Retrieve a list of baskets a user is permissioned to

    :param user_id: Marquee user/app ID (default is current application's id)
    :return: dataframe of baskets user has access to

    **Usage**

    Retrieve a list of baskets a user is permissioned to

    **Examples**

    Retrieve a list of baskets the current user is permissioned to

    >>> from gs_quant.markets.indices_utils import *
    >>>
    >>> get_my_baskets()
    """
    user_id = user_id if user_id is not None else GsSession.current.client_id
    tag = f'Custom Basket:{user_id}'
    response = GsMonitorsApi.get_monitors(tags=tag)
    if len(response):
        row_groups = get(response, '0.parameters.row_groups')
        my_baskets = []
        for row_group in row_groups:
            entity_ids = [entity.id for entity in row_group.entity_ids]
            baskets = GsAssetApi.get_many_assets_data(id=entity_ids, fields=['id', 'ticker', 'name', 'liveDate'])
            my_baskets += [dict(monitor_name=row_group.name, id=get(basket, 'id'), ticker=get(basket, 'ticker'),
                                name=get(basket, 'name'), live_date=get(basket, 'liveDate')) for basket in baskets]
        return pd.DataFrame(my_baskets)


def get_flagship_baskets(fields: List[str] = [],
                         basket_type: List[BasketType] = BasketType.to_list(),
                         asset_class: List[AssetClass] = [AssetClass.Equity],
                         region: List[Region] = None,
                         styles: List[Union[CustomBasketStyles, ResearchBasketStyles]] = None,
                         as_of: dt.datetime = None) -> pd.DataFrame:
    """
    Retrieve flagship baskets

    :param fields: Fields to retrieve in addition to mqid, name, ticker, region, basket type, \
        description, styles, live date, and asset class
    :param basket_type: Basket type(s)
    :param asset_class: Asset class (defaults to Equity)
    :param region: Basket region(s)
    :param styles: Basket style(s)
    :param as_of: Datetime for which to retrieve baskets (defaults to current time)
    :return: flagship baskets

    **Usage**

    Retrieve a list of flagship baskets

    **Examples**

    Retrieve a list of flagship baskets

    >>> from gs_quant.markets.indices_utils import *
    >>>
    >>> get_flagship_baskets()

    **See also**

    :func:`get_flagships_with_assets` :func:`get_flagships_performance` :func:`get_flagships_constituents`
    """
    fields = list(set(fields).union(set(['id', 'name', 'ticker', 'region', 'type', 'description',
                                         'styles', 'liveDate', 'assetClass'])))
    query = dict(fields=fields, type=basket_type, asset_class=asset_class, is_pair_basket=[False], flagship=[True])
    if region is not None:
        query.update(region=region)
    if styles is not None:
        query.update(styles=styles)
    response = GsAssetApi.get_many_assets_data_scroll(**query, as_of=as_of, limit=2000, scroll='1m')
    return pd.DataFrame(response)


def get_flagships_with_assets(identifiers: List[str],
                              fields: List[str] = [],
                              basket_type: List[BasketType] = BasketType.to_list(),
                              asset_class: List[AssetClass] = [AssetClass.Equity],
                              region: List[Region] = None,
                              styles: List[Union[CustomBasketStyles, ResearchBasketStyles]] = None,
                              as_of: dt.datetime = None) -> pd.DataFrame:
    """
    Retrieve a list of flagship baskets containing specified assets

    :param identifiers: List of asset identifiers
    :param fields: Fields to retrieve in addition to mqid, name, ticker, region, basket type, \
        description, styles, live date, and asset class
    :param basket_type: Basket type(s)
    :param asset_class: Asset class (defaults to Equity)
    :param region: Basket region(s)
    :param styles: Basket style(s)
    :param as_of: Datetime for which to retrieve baskets (defaults to current time)
    :return: flagship baskets containing specified assets

    **Usage**

    Retrieve a list of flagship baskets containing specified assets

    **Examples**

    Retrieve a list of flagship custom baskets containing 'AAPL UW' single stock

    >>> from gs_quant.markets.indices_utils import *
    >>>
    >>> get_flagships_with_assets(identifiers=['AAPL UW'], basket_type=[BasketType.CUSTOM_BASKET])

    **See also**

    :func:`get_flagship_baskets` :func:`get_flagships_performance` :func:`get_flagships_constituents`
    """
    fields = list(set(fields).union(set(['id', 'name', 'ticker', 'region', 'type', 'description',
                                         'styles', 'liveDate', 'assetClass'])))
    response = GsAssetApi.resolve_assets(identifier=identifiers, fields=['id'], limit=1)
    mqids = [get(asset, '0.id') for asset in response.values()]
    query = dict(fields=fields, type=basket_type, asset_class=asset_class, is_pair_basket=[False],
                 flagship=[True], underlying_asset_ids=mqids)
    if region is not None:
        query.update(region=region)
    if styles is not None:
        query.update(styles=styles)
    response = GsAssetApi.get_many_assets_data_scroll(**query, as_of=as_of, limit=2000, scroll='1m')
    return pd.DataFrame(response)


def get_flagships_performance(fields: List[str] = [],
                              basket_type: List[BasketType] = BasketType.to_list(),
                              asset_class: List[AssetClass] = [AssetClass.Equity],
                              region: List[Region] = None,
                              styles: List[Union[CustomBasketStyles, ResearchBasketStyles]] = None,
                              start: dt.date = None,
                              end: dt.date = None,) -> pd.DataFrame:
    """
    Retrieve performance data for flagship baskets

    :param fields: Fields to retrieve in addition to bbid, mqid, name, region, basket type, \
        styles, live date, and asset class
    :param basket_type: Basket type(s)
    :param asset_class: Asset class (defaults to Equity)
    :param region: Basket region(s)
    :param styles: Basket style(s)
    :param start: Date for which to retrieve pricing (defaults to previous business day)
    :param end: Date for which to retrieve pricing (defaults to previous business day)
    :return: pricing data for flagship baskets

    **Usage**

    Retrieve performance data for flagship baskets

    **Examples**

    Retrieve performance data for flagship Asia custom baskets

    >>> from gs_quant.markets.indices_utils import *
    >>>
    >>> get_flagships_performance(basket_type=[BasketType.CUSTOM_BASKET], region=[Region.ASIA])

    **See also**

    :func:`get_flagships_with_assets` :func:`get_flagship_baskets` :func:`get_flagships_constituents`
    """
    start = start or prev_business_date()
    end = end or prev_business_date()
    fields = list(set(fields).union(set(['name', 'region', 'type', 'flagship', 'isPairBasket',
                                         'styles', 'liveDate', 'assetClass'])))
    coverage = GsDataApi.get_coverage(dataset_id=IndicesDatasets.GSCB_FLAGSHIP.value, fields=fields)
    basket_regions = [] if region is None else [r.value for r in region]
    basket_styles = [] if styles is None else [s.value for s in styles]
    basket_types = [b_type.value for b_type in basket_type]
    baskets_map = {}
    for basket in coverage:
        if get(basket, 'flagship') is False or get(basket, 'isPairBasket') is True or \
            region is not None and get(basket, 'region') not in basket_regions or \
                get(basket, 'type') not in basket_types or \
                get(basket, 'assetClass') not in [a.value for a in asset_class] or \
                styles is not None and not any(s in get(basket, 'styles', []) for s in basket_styles):
            continue
        baskets_map[get(basket, 'assetId')] = basket
    response = GsDataApi.query_data(query=DataQuery(where=dict(assetId=list(baskets_map.keys())),
                                    startDate=start, endDate=end), dataset_id=IndicesDatasets.GSCB_FLAGSHIP.value)
    performance = []
    for basket in response:
        basket_data = baskets_map[get(basket, 'assetId')]
        basket_data.update(closePrice=get(basket, 'closePrice'))
        basket_data.update(date=get(basket, 'date'))
        performance.append(basket_data)
    return pd.DataFrame(performance)


def get_flagships_constituents(fields: List[str] = [],
                               basket_type: List[BasketType] = BasketType.to_list(),
                               asset_class: List[AssetClass] = [AssetClass.Equity],
                               region: List[Region] = None,
                               styles: List[Union[CustomBasketStyles, ResearchBasketStyles]] = None,
                               start: dt.date = None,
                               end: dt.date = None,) -> pd.DataFrame:
    """
    Retrieve flagship baskets constituents

    :param fields: Fields to retrieve in addition to mqid, name, ticker, region, basket type, \
        styles, live date, and asset class
    :param basket_type: Basket type(s)
    :param asset_class: Asset class (defaults to Equity)
    :param region: Basket region(s)
    :param styles: Basket style(s)
    :param start: Start date for which to retrieve constituents (defaults to previous business day)
    :param end: End date for which to retrieve constituents (defaults to previous business day)
    :return: flagship baskets constituents

    **Usage**

    Retrieve flagship baskets constituents

    **Examples**

    Retrieve a list of flagship baskets constituents

    >>> from gs_quant.markets.indices_utils import *
    >>>
    >>> get_flagships_constituents()

    **See also**

    :func:`get_flagships_with_assets` :func:`get_flagships_performance` :func:`get_flagship_baskets`
    """
    start = start or prev_business_date()
    end = end or prev_business_date()
    basket_fields = list(set(fields).union(set(['id', 'name', 'ticker', 'region', 'type', 'styles',
                                                'liveDate', 'assetClass'])))
    fields = list(set(fields).union(set(['id', 'name'])))
    query = dict(fields=basket_fields, type=basket_type, asset_class=asset_class,
                 is_pair_basket=[False], flagship=[True])
    if region is not None:
        query.update(region=region)
    if styles is not None:
        query.update(styles=styles)

    coverage_results = ThreadPoolManager.run_async([
        partial(GsAssetApi.get_many_assets_data_scroll, **query, limit=2000, scroll='1m'),
        partial(GsDataApi.get_coverage, dataset_id=IndicesDatasets.GSCB_FLAGSHIP.value, fields=['type', 'bbid'],
                include_history=True)
    ])
    basket_data, coverage = coverage_results[0], coverage_results[1]
    basket_map = {get(basket, 'id'): basket for basket in basket_data}

    tasks, results = [], []
    for b in coverage:
        tasks.append(partial(__get_constituents_data, basket=b, basket_map=basket_map, start=start,
                             end=end, fields=fields))
    tasks = [tasks[i * 50:(i + 1) * 50] for i in range((len(tasks) + 50 - 1) // 50)]
    for task in tasks:
        results += ThreadPoolManager.run_async(task)
        sleep(1)

    return pd.DataFrame([r for r in results if r is not None])


def __get_constituents_data(basket: Dict, basket_map: Dict, start: dt.date,
                            end: dt.date, fields: List[str]) -> List:
    _id, _type = get(basket, 'assetId'), get(basket, 'type')
    if _id not in list(basket_map.keys()):
        return
    start_date = dt.datetime.strptime(basket['historyStartDate'], '%Y-%m-%d').date()
    # only query for dates after/on first date with availability
    start_date = start_date if start < start_date else start
    # make sure start date is not greater than end date
    end_date = start_date if start_date > end else end

    dataset_id = IndicesDatasets.GSBASKETCONSTITUENTS.value if _type == BasketType.CUSTOM_BASKET.value\
        else IndicesDatasets.GIRBASKETCONSTITUENTS.value
    data = GsDataApi.query_data(query=DataQuery(where=dict(assetId=_id), startDate=start_date,
                                                endDate=end_date), dataset_id=dataset_id)

    asset_ids = list(set([d['underlyingAssetId'] for d in data]))
    asset_data = GsAssetApi.get_many_assets_data_scroll(id=asset_ids, fields=fields,
                                                        limit=2000, scroll='1m')
    asset_data_map = {get(asset, 'id'): asset for asset in asset_data}

    for d in data:
        asset_id = get(d, 'underlyingAssetId', '')
        asset_id_map = get(asset_data_map, asset_id, {})
        for f in fields:
            d[f] = get(asset_id_map, f)
    basket_map[_id].update(constituents=data)
    return basket_map[_id]
