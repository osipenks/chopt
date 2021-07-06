import logging
import datetime
from typing import Any, Dict
from pathlib import Path
import os.path

from freqtrade.exchange import timeframe_to_minutes, timeframe_to_prev_date
from freqtrade.commands import start_download_data
from freqtrade.misc import pair_to_filename

from .utils import setup_configuration

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def start_data_load(args: Dict[str, Any]) -> None:
    """
    Start data download
    :param args: Cli args from Arguments()
    :return: None
    """
    logger.info('Starting data load...')

    dd = DataDownload(args)

    if dd.load_data():
        logger.info('Data load finished.')
        return


class DataDownload:

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

    def _download_data(self, download_args):
        try:
            start_download_data(download_args)
        except Exception as e:
            logger.error(f"Data download: {e}")
            return False
        return True

    def pair_trades_filename(self, datadir: Path, pair: str) -> Path:
        file_extension = 'json.gz'
        pair_s = pair_to_filename(pair)
        filename = datadir.joinpath(f'{pair_s}-trades.{file_extension}')
        return filename

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
            'dry_run': True,
            'dry_run_wallet': 1000,
        }

        for pair in self.config['pairs']:

            download_args.update({'pairs': [pair]})

            if not self._download_data(download_args):

                data_file_name = self.pair_trades_filename(Path(self.data_dir), pair)
                data_downloaded = False
                for i in range(1, 4):
                    logger.info(
                        f"Data download finished with error, trying to remove data file and download from scratch ({i})...")
                    try:
                        os.remove(data_file_name)
                    except OSError:
                        pass
                    data_downloaded = self._download_data(download_args)
                    if data_downloaded:
                        break

                if not data_downloaded:
                    # nothing helped
                    # todo: exclude pair
                    return False

        return True
