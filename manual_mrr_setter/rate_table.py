# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

"""Manual MRR Setter Rate Table

This module contains functions to derive a table of statistics for rate and power used for packet transmission.
"""
import datetime
import os

__all__ = ["RateStatistics"]


class RateStatistics:
    def __init__(self, sta, save_statistics=False, output_dir=None):
        self._init_stats(sta.stats)
        self._last_updated = dict()
        self._last_updated["timestamp"] = sta.last_seen
        self._last_updated["rates"] = []
        self._ap_name = sta.accesspoint.name
        self._radio = sta.radio
        self._sta_name = sta.mac_addr
        self._save_statistics = save_statistics
        if save_statistics:
            self._msmt_dir = output_dir if output_dir else os.getcwd()
            self._setup_output_file()

    @property
    def save_statistics(self):
        return self._save_statistics

    def _init_stats(self, sta_stats):
        self._stats = dict()

        for rate in sta_stats.keys():
            self._stats[rate] = dict()
            for txpower in sta_stats[rate].keys():
                self._stats[rate][txpower] = dict()
                self._stats[rate][txpower]["hist_attempts"] = sta_stats[rate][txpower]["attempts"]
                self._stats[rate][txpower]["hist_success"] = sta_stats[rate][txpower]["success"]
                self._stats[rate][txpower]["cur_attempts"] = sta_stats[rate][txpower]["attempts"]
                self._stats[rate][txpower]["cur_success"] = sta_stats[rate][txpower]["success"]
                self._stats[rate][txpower]["timestamp"] = sta_stats[rate][txpower]["timestamp"]
                if (
                    self._stats[rate][txpower]["cur_attempts"]
                    or self._stats[rate][txpower]["cur_success"]
                ) == 0:
                    self._stats[rate][txpower]["cur_success_prob"] = 0
                    self._stats[rate][txpower]["hist_success_prob"] = 0
                else:
                    self._stats[rate][txpower]["cur_success_prob"] = (
                        self._stats[rate][txpower]["cur_success"]
                        / self._stats[rate][txpower]["cur_attempts"]
                    )
                    self._stats[rate][txpower]["hist_success_prob"] = (
                        self._stats[rate][txpower]["cur_success"]
                        / self._stats[rate][txpower]["cur_attempts"]
                    )

    @property
    def updated_rates(self):
        stats_subset = dict()
        for rate, txpower in self._last_updated["rates"]:
            if rate not in stats_subset:
                stats_subset[rate] = dict()
            stats_subset[rate][txpower] = self._stats[rate][txpower]

        return stats_subset

    @property
    def last_updated(self):
        return self._last_updated

    @property
    def hist_stats(self):
        return 1

    def update(self, timestamp: int, new_stats: dict):
        self._last_updated["rates"] = list()

        for rate in new_stats.keys():
            for txpower in new_stats[rate].keys():
                if new_stats[rate][txpower]["timestamp"] > self._stats[rate][txpower]["timestamp"]:
                    self._stats[rate][txpower]["cur_success"] = (
                        new_stats[rate][txpower]["success"]
                        - self._stats[rate][txpower]["hist_success"]
                    )

                    self._stats[rate][txpower]["cur_attempts"] = (
                        new_stats[rate][txpower]["attempts"]
                        - self._stats[rate][txpower]["hist_attempts"]
                    )

                    self._stats[rate][txpower]["cur_success_prob"] = (
                        self._stats[rate][txpower]["cur_success"]
                        / self._stats[rate][txpower]["cur_attempts"]
                    )

                    self._stats[rate][txpower]["hist_success"] = new_stats[rate][txpower]["success"]

                    self._stats[rate][txpower]["hist_attempts"] = new_stats[rate][txpower][
                        "attempts"
                    ]

                    self._stats[rate][txpower]["hist_success_prob"] = (
                        self._stats[rate][txpower]["hist_success"]
                        / self._stats[rate][txpower]["hist_attempts"]
                    )
                    self._stats[rate][txpower]["timestamp"] = new_stats[rate][txpower]["timestamp"]

                    self._last_updated["rates"].append((rate, txpower))

        self._last_updated["timestamp"] = timestamp

        if self._save_statistics:
            self._print_stats()

    def get_stats(self):
        return self._stats

    def _print_stats(self):
        self._output_file.write(
            f"%%-------Updated Rates {hex(self._last_updated['timestamp'])}----------%%\n"
        )
        for rate, txpower in self._last_updated["rates"]:
            self._output_file.write(
                f"{rate}, {txpower}: cur_attempts {self._stats[rate][txpower]['cur_attempts']},  "
                f"cur_success {self._stats[rate][txpower]['cur_success']}, "
                f"hist_attempts {self._stats[rate][txpower]['hist_attempts']},  "
                f"hist_success {self._stats[rate][txpower]['hist_success']} \n"
            )

    def best_rates_success_prob(self):
        best_rates = []
        # for rate, txpower in self._stats:
        #     if self._stats[rate][txpower]["hist_success_prob"] < self._stats[best_rates[-1][0]][best_rates[-1][1]]["hist_success_prob"]:
        #         continue
        #     else:
        #         for rate1, txpower1 in best_rates:
        #             if self._stats[rate][txpower]["hist_success_prob"] > self._stats[rate1][txpower1]["hist_success_prob"]:
        #
        pass

    def best_rates_throughput(self):
        pass

    def _setup_output_file(self):
        """
        Creates all the required folders to store the rate control output
        files such as rc_stats and rc_stats_csv.

        """
        output_file_dir = os.path.join(
            self._msmt_dir,
            "mmrrs_rate_statistics",
            self._ap_name,
            self._radio,
            self._sta_name.replace(":", "-"),
        )

        os.makedirs(output_file_dir, exist_ok=True)
        self._output_file_path = os.path.join(output_file_dir, "rate_stats")
        self._output_file = open(self._output_file_path, "w")
