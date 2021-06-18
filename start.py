import logging
from typing import Any, Dict

from freqtrade.exceptions import OperationalException
from pprint import pprint
from freqtrade.exchange import timeframe_to_minutes, timeframe_to_prev_date
import datetime

from freqtrade.commands import start_backtesting, start_convert_data, start_download_data
from .utils import hyperopt_run, setup_chopt_configuration, human_report_hyperopt
from .chopt import ContinuousHyperOpt

import rapidjson
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def start_continuous_hyperopt(args: Dict[str, Any]) -> None:
    """
    Start continuous hyperopt
    :param args: Cli args from Arguments()
    :return: None
    """
    logger.info('Starting continuous hyperopt...')

    chopt = ContinuousHyperOpt(args)

    if not chopt.load_data():
        return

    logger.info('Data download finished. Starting HyperOpt...   ')

    chopt.hyperopt_epochs = 900
    chopt.run_hyperopt()

