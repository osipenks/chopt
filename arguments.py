"""
This module contains the argument manager class
"""
import argparse
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional

from freqtrade.commands.cli_options import AVAILABLE_CLI_OPTIONS, Arg
from freqtrade.constants import DEFAULT_CONFIG

from freqtrade.commands import Arguments

ARGS_COMMON = ["verbosity", "logfile", "version",
               "config", "datadir", "user_data_dir",
               "timeframe", "timerange", "dataformat_ohlcv",
               "max_open_trades", "stake_amount", "fee",
               "pairs", "db_url", "sd_notify",
               "dry_run", "dry_run_wallet", "position_stacking",
               "use_max_market_positions", "enable_protections", "strategy_list",
               "export", "exportfilename", "hyperopt",
               "hyperopt_path", "epochs", "spaces",
               "print_json",
               "hyperopt_jobs", "hyperopt_random_state", "hyperopt_min_trades", "hyperopt_loss",
               "pairs_file", "days", "new_pairs_days",
               "download_trades", "exchange", "timeframes", "erase",
               "dataformat_trades", "strategy", "strategy_path",
               "backperiod",
               ]

NO_CONF_REQURIED = ["convert-data", "convert-trade-data", "download-data", "list-timeframes",
                    "list-markets", "list-pairs", "list-strategies", "list-data",
                    "list-hyperopts", "hyperopt-list", "hyperopt-show",
                    "plot-dataframe", "plot-profit", "show-trades"]

NO_CONF_ALLOWED = ["create-userdir", "list-exchanges", "new-hyperopt", "new-strategy"]


AVAILABLE_CLI_OPTIONS.update({
            "backperiod": Arg(
                '-backperiod', '--backperiod',
                help='Look back timeperiod',
                type=int,
                metavar='INT',
            ),
        })

class ChoptArguments(Arguments):
    """
    Arguments Class. Manage the arguments received by the cli
    """

    def get_parsed_arg(self) -> Dict[str, Any]:
        """
        Return the list of arguments
        :return: List[str] List of arguments
        """
        if self._parsed_arg is None:
            self._build_subcommands()
            self._parsed_arg = self._parse_args()

        return vars(self._parsed_arg)

    def _parse_args(self) -> argparse.Namespace:
        """
        Parses given arguments and returns an argparse Namespace instance.
        """
        parsed_arg = self.parser.parse_args(self.args)

        return parsed_arg

    def _build_args(self, optionlist, parser):

        for val in optionlist:
            opt = AVAILABLE_CLI_OPTIONS[val]
            parser.add_argument(*opt.cli, dest=val, **opt.kwargs)

    def _build_subcommands(self) -> None:
        """
        Builds and attaches all subcommands.
        :return: None
        """
        # Build shared arguments (as group Common Options)
        _common_parser = argparse.ArgumentParser(add_help=False)
        group = _common_parser.add_argument_group("Common arguments")
        self._build_args(optionlist=ARGS_COMMON, parser=group)

        self.parser = _common_parser

        # self.parser = argparse.ArgumentParser(description='Free, open source crypto trading bot')
        # self._build_args(optionlist=['version'], parser=self.parser)
