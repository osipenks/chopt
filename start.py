import logging
from typing import Any, Dict
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

    # if not chopt.load_data():
    #     return

    logger.info('Data download finished. Starting HyperOpt...   ')

    chopt.hyperopt_epochs = 900
    chopt.hyperopt_jobs = 4
    chopt.run_hyperopt()

