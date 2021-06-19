import logging
import os.path
from typing import Any, Dict
import json

from pprint import pprint
from freqtrade.exchange import timeframe_to_minutes, timeframe_to_prev_date
from freqtrade.misc import pair_to_filename
import datetime

from freqtrade.commands import start_backtesting, start_convert_data, start_download_data
from .utils import hyperopt_run, setup_chopt_configuration, human_report_hyperopt

from pathlib import Path

logger = logging.getLogger(__name__)


class ContinuousHyperOpt:

    def __init__(self, args: Dict[str, Any]) -> None:

        self.strategy = args['strategy']
        self.config_files = args['config']
        self.back_period = args.get("backperiod", 864)
        self.config = setup_chopt_configuration(args)

        self.bot_name = self.config['bot_name']
        self.timeframe = self.config['timeframe']
        self.pair_list = self.config["pairs"]
        self.data_dir = self.config['datadir']

        self.name = f'{self.bot_name} {self.strategy}'
        self.hyperopt_loss = 'SortinoHyperOptLossDaily'

        end_date = timeframe_to_prev_date(self.timeframe)
        start_date = end_date - datetime.timedelta(minutes=self.back_period * timeframe_to_minutes(self.timeframe))
        self.timerange_str = f'{start_date.strftime("%Y%m%d")}-{end_date.strftime("%Y%m%d")}'

        self.dry_run_wallet = 1000
        self.hyperopt_spaces = ['buy', 'sell', 'roi']
        self.hyperopt_epochs = 900
        self.hyperopt_random_stat = 0
        self.hyperopt_enable_protections = False
        self.hyperopt_min_trades = 5
        self.hyperopt_jobs = 8

        logger.info(f'Instantiated chopt for {self.name}, timerange {self.timerange_str}')

    def _download_data(self, download_args):
        try:
            start_download_data(download_args)
        except Exception as e:
            logger.error(f"Data download: {e}")
            return False
        return True

    def load_data(self):
        """
        Download market data for selected timerange
        """

        logger.info(f'Start data download for {self.name} time range {self.timerange_str}')
        download_args = {
            'config': self.config_files,
            'timeframes': [self.timeframe],
            'pairs': self.config['pairs'],
            'timerange': self.timerange_str,
        }

        for pair in self.config['pairs']:

            download_args.update({'pairs': [pair]})

            if not self._download_data(download_args):

                data_file_name = self.pair_trades_filename(Path(self.data_dir), pair)
                for i in range(1, 4):
                    logger.info(
                        f"Data download finished with error, trying to remove data file and download from scratch ({i})...")
                    try:
                        os.remove(data_file_name)
                    except OSError:
                        pass
                    if self._download_data(download_args):
                        return True

                return False

        return True

    def save_opted_params(self, params_dict: Dict[str, Any]) -> None:

        dir_path = os.path.join(self.config['user_data_dir'], 'chopt')
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)

        full_path = os.path.join(dir_path, f'{self.bot_name}_{self.strategy}.json')
        with Path(full_path).open('w') as f:
            json.dump(params_dict, f, indent=4)
            f.write("\n")

    def run_hyperopt(self):
        """
        Start hyperopt process
        """

        logger.info(f'Loaded config for {self.name}, {len(self.pair_list)} pairs in whitelist')

        config = setup_chopt_configuration({
                'hyperopt_loss': self.hyperopt_loss,
                'strategy': self.strategy,
                'config': self.config_files,
                'pairs': self.pair_list,
                'timerange': self.timerange_str,
                'dry_run_wallet': self.dry_run_wallet,
                'dry_run': True,
                'spaces': self.hyperopt_spaces,
                'epochs': self.hyperopt_epochs,
                'hyperopt_random_stat': self.hyperopt_random_stat,
                'hyperopt_enable_protections': self.hyperopt_enable_protections,
                'hyperopt_min_trades': self.hyperopt_min_trades,
                'hyperopt_jobs': self.hyperopt_jobs,
            })
        config['pairlists'] = [{'method': 'StaticPairList'}]
        config['dry_run'] = True

        hyperopt_res = hyperopt_run(config)

        if not hyperopt_res.get('results_metrics', False):
            logger.error(f'Hyperopt finished, no results obtained')
            return False

        logger.info(f'Hyperopt finished:\n{human_report_hyperopt(hyperopt_res)}. {self.name}')

        params_json = {}

        params = hyperopt_res['params_details']
        if params:
            pair = 'default'

            now = datetime.datetime.now()
            params_json[pair] = {'hyperopt_datetime': now.strftime("%Y-%m-%d %H:%M:%S")}

            for key, val in params['buy'].items():
                params_json[pair][key] = val

            for key, val in params['sell'].items():
                params_json[pair][key] = val

            min_roi = {}
            for key, val in params['roi'].items():
                min_roi[int(key)] = round(val, 3)
            params_json[pair]['minimal_roi'] = min_roi

            logger.info(f'Parameters:\n{params_json}')

        self.save_opted_params(params_json)

        return True

    def pair_trades_filename(self, datadir: Path, pair: str) -> Path:
        file_extension = 'json.gz'
        pair_s = pair_to_filename(pair)
        filename = datadir.joinpath(f'{pair_s}-trades.{file_extension}')
        return filename
