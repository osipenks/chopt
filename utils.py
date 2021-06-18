import logging
from typing import Any, Dict
import rapidjson
from pathlib import Path

from freqtrade import constants
from freqtrade.exceptions import OperationalException
from freqtrade.misc import round_coin_value
from freqtrade.configuration import Configuration

logger = logging.getLogger(__name__)


def hyperopt_run(args: Dict[str, Any]):
    """
    Start hyperopt script
    :param args: Cli args from Arguments()
    :return: None
    """
    # Import here to avoid loading hyperopt module when it's not used
    try:
        from filelock import FileLock, Timeout

        from freqtrade.optimize.hyperopt import Hyperopt
    except ImportError as e:
        raise OperationalException(
            f"{e}. Please ensure that the hyperopt dependencies are installed.") from e
    # Initialize configuration
    config = setup_chopt_configuration(args)

    logger.info('Starting freqtrade in Hyperopt mode')

    lock = FileLock(Hyperopt.get_lock_filename(config))

    hyperopt_res = {}

    try:
        with lock.acquire(timeout=1):

            # Remove noisy log messages
            logging.getLogger('hyperopt.tpe').setLevel(logging.WARNING)
            logging.getLogger('filelock').setLevel(logging.WARNING)

            # Initialize backtesting object
            hyperopt = Hyperopt(config)
            hyperopt.start()

            if hyperopt.results_file:

                with hyperopt.results_file.open('r') as f:
                    hyperopts = [rapidjson.loads(line.rstrip()) for line in f]
                    for r in hyperopts:
                        if r and r['is_best']:
                            hyperopt_res = r
            else:
                raise OperationalException(f'No hyperopt result file found.')

    except Timeout:
        logger.info("Another running instance of freqtrade Hyperopt detected.")
        logger.info("Simultaneous execution of multiple Hyperopt commands is not supported. "
                    "Hyperopt module is resource hungry. Please run your Hyperopt sequentially "
                    "or on separate machines.")
        logger.info("Quitting now.")

    return hyperopt_res


def setup_chopt_configuration(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare the configuration for the Hyperopt module
    :param args: Cli args from Arguments()
    :return: Configuration
    """
    configuration = Configuration(args)

    config = configuration.get_config()

    if (config['stake_amount'] != constants.UNLIMITED_STAKE_AMOUNT
            and config['stake_amount'] > config['dry_run_wallet']):
        wallet = round_coin_value(config['dry_run_wallet'], config['stake_currency'])
        stake = round_coin_value(config['stake_amount'], config['stake_currency'])
        raise OperationalException(f"Starting balance ({wallet}) "
                                   f"is smaller than stake_amount {stake}.")

    return config


def human_report_hyperopt(hyperopt_res):
    metrics = hyperopt_res['results_metrics']

    total_trades = metrics['total_trades']
    trades_per_day = metrics['trades_per_day']

    wins = metrics['wins']
    draws = metrics['draws']
    losses = metrics['losses']

    winrate = wins / total_trades if total_trades else 1

    profit_mean = metrics['profit_mean']
    profit_median = metrics['profit_median']
    profit_total = metrics['profit_total']
    profit_total_abs = metrics['profit_total_abs']

    winner_holding_avg = metrics['winner_holding_avg']
    holding_avg = metrics['holding_avg']
    loser_holding_avg = metrics['loser_holding_avg']

    report_str = f'Profit {profit_total_abs:.2f} {metrics["stake_currency"]} ( {profit_total * 100:.2f}%), avg. {profit_mean * 100:.2f}%, ' \
                 f'{total_trades} trades, {wins}/{draws}/{losses} wins/draws/losses, win rate {winrate * 100:.2f}%, ' \
                 f'trades per day {trades_per_day}, ' \
                 f'avg. duration {holding_avg}, winner {winner_holding_avg}, loser {loser_holding_avg}'

    return report_str


def load_file(self, path: Path) -> Dict[str, Any]:
    try:
        with path.open('r') as file:
            file_dict = rapidjson.load(file, parse_mode=rapidjson.PM_COMMENTS | rapidjson.PM_TRAILING_COMMAS)
    except FileNotFoundError:
        raise OperationalException(f'File "{path}" not found!')
    return file_dict


