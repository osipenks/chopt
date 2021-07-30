import logging
from typing import Any, Dict
import datetime
from pathlib import Path
import pandas as pd
from prophet import Prophet

from freqtrade.exchange import timeframe_to_minutes, timeframe_to_prev_date
from freqtrade.data.history import load_pair_history
from .utils import setup_configuration
from .model_storage import ModelStorageChopt

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
        logger.info(f'Trend for {pair}:')
        trend.run(pair)


class Trend:

    def __init__(self, args: Dict[str, Any]) -> None:
        self.config_files = args['config']
        self.back_period = args.get("backperiod", 20520)   # 3 month
        self.config = setup_configuration(args)

        self.config['dry_run'] = True

        self.bot_name = self.config['bot_name']
        self.timeframe = self.config['timeframe']
        self.pair_list = self.config["pairs"]
        self.data_dir = self.config['datadir']

        self.name = f'{self.bot_name}'

        self.end_date = timeframe_to_prev_date(self.timeframe)
        self.start_date = self.end_date - datetime.timedelta(
            minutes=self.back_period * timeframe_to_minutes(self.timeframe))
        self.timerange_str = f'{self.start_date.strftime("%Y%m%d")}-{self.end_date.strftime("%Y%m%d")}'

        self.data_location = Path(self.config['user_data_dir'], 'data', 'kraken')

        self.dry_run_wallet = 1000

        logger.info(f'Trend instantiated for {self.name}, timerange {self.timerange_str}')

    def run(self, pair):

        # Load historical data
        hist_df = load_pair_history(datadir=self.data_location, timeframe=self.timeframe, pair=pair)
        hist_df = hist_df.set_index('date', drop=False)
        logger.info(f'Loaded {len(hist_df)} candles for {pair}')

        forecast_days_ahead = 1

        future_end_date = self.end_date + datetime.timedelta(
            minutes=forecast_days_ahead * timeframe_to_minutes(self.timeframe))
        df = hist_df[self.start_date:future_end_date]

        logger.info(f'Selected {len(df)} candles for trend calculation, time range {self.start_date} - {self.end_date}')
        logger.info(
            f'Timed data starts at {df.head(1)["date"].to_numpy()[0]},  ends {df.tail(1)["date"].to_numpy()[0]}')

        datetime_df = pd.to_datetime(df['date'].copy(deep=True)).dt.tz_localize(None)

        ts = pd.DataFrame({'ds': datetime_df, 'y': df['close']})

        """
        Fit Prophet model and make prediction 
        """
        m = Prophet(changepoint_prior_scale=1.0, changepoint_range=1.0)
        m.fit(ts)
        logger.info(f'Model fitted and ready to predict')
        future = m.make_future_dataframe(periods=forecast_days_ahead)
        forecast = m.predict(future)
        logger.info(f'Prediction made for {forecast_days_ahead} day(s)')

        formatted_dct = {}
        trend_df = pd.DataFrame({'date': forecast['ds'], 'trend': forecast['trend']})
        trend_df = trend_df.set_index('date', drop=False)
        dct = trend_df['trend'].to_dict()
        for k, v in dct.items():
            formatted_dct[k.isoformat()] = v

        ms = ModelStorageChopt(Path(self.config['user_data_dir']))

        pair_label = pair.replace("/", "").lower()
        storage_key = f'trend_forecast.{pair_label}'
        ms.save(storage_key, formatted_dct)
        logger.info(f'{pair} trend saved to {ms.key_to_path(storage_key)}')

        """
        Position size calculation
        """
        pos_pct_for_max_drawdown = 0.2

        trend_df['pct_change'] = trend_df['trend'].pct_change(72)
        max_drawdown = trend_df["pct_change"].min()
        if max_drawdown >= 0:
            max_drawdown = -0.1

        trend_df['pos_pct'] = 1 - ((1 - pos_pct_for_max_drawdown) / abs(max_drawdown)) * abs(
            trend_df[(trend_df['pct_change'] < 0)]['pct_change'])

        trend_df['pos_pct'].fillna(1, inplace=True)

        # Position size based on most recent trend (i.e. predicted for the next day)
        trend_tail = trend_df.tail(1).to_dict()
        stake_coef = round(list(trend_tail['pos_pct'].values())[0], 5)
        forecast_date = list(trend_tail['date'].values())[0].isoformat()

        storage_key = f'pos_size_trend.{pair_label}'
        ms.save(storage_key, {'pos_size': stake_coef, 'forecast_date': forecast_date})
        logger.info(f'{pair} position size {stake_coef} saved to {ms.key_to_path(storage_key)}')

        return True
