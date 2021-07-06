import logging
from typing import Any, Dict
import datetime
import pandas as pd
from prophet import Prophet
import numpy as np

from freqtrade.exchange import timeframe_to_minutes, timeframe_to_prev_date
from .utils import setup_configuration

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def start_trend(args: Dict[str, Any]) -> None:
    """
    Start trend calculation and forecast
    :param args: Cli args from Arguments()
    :return: None
    """
    trend = Trend(args)

    for pair in trend.pair_list:
        logger.info(f'Trend for {pair}')
        trend.fit(pair)


class Trend:

    def __init__(self, args: Dict[str, Any]) -> None:
        self.config_files = args['config']
        self.back_period = args.get("backperiod", 864)
        self.config = setup_configuration(args)

        self.config['dry_run'] = True

        self.bot_name = self.config['bot_name']
        self.timeframe = self.config['timeframe']
        self.pair_list = self.config["pairs"]
        self.data_dir = self.config['datadir']

        self.name = f'{self.bot_name}'

        end_date = timeframe_to_prev_date(self.timeframe)
        start_date = end_date - datetime.timedelta(minutes=self.back_period * timeframe_to_minutes(self.timeframe))
        self.timerange_str = f'{start_date.strftime("%Y%m%d")}-{end_date.strftime("%Y%m%d")}'

        self.dry_run_wallet = 1000

        logger.info(f'Data download instantiated for {self.name}, timerange {self.timerange_str}')

    def fit(self, pair):
        return True
