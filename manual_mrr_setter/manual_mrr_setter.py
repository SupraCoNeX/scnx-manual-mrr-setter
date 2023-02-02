# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import asyncio
import time
import random
import logging
import copy

__all__ = [
    "ManualMRRSetter",
    "start",
]


class ManualMRRSetter:
    def __init__(self, ap, radio, **options):
        self._loop = ap.loop
        self._ap = ap
        self._radio = radio
        self._rc_stations = dict()
        self._interval_ns = options.get("interval_ns", 100e6)
        self._multi_rate_retry = options.get("multi_rate_retry", "lowest;1")
        self._logger = ap.logger

    async def _wait_for_stations(self):
        """
        This async function waits for RateMan to add at least one station and its rate stats.

        """
        while True:
            try:
                if self._ap.get_stations(self._radio):
                    break
                else:
                    self._logger.debug(
                        f"{self._ap.name}: Waiting for at least one station"
                    )
                    await asyncio.sleep(0.01)
                    self._ap.enable_manual_mode(self._radio)

            except (KeyboardInterrupt, OSError, IOError, asyncio.CancelledError):
                break

    async def execute_rate_setting(self):
        """
        Create an asyncio task per station to execute rate setting per station.

        """

        self._logger.info(f"{self._ap.name}:{self._radio}: Starting Manual MRR Setter")

        await self._wait_for_stations()
        self._ap.reset_rate_stats(self._radio)

        while True:
            await asyncio.sleep(0.1)
            try:
                for mac_addr, station in self._ap.get_stations(self._radio).items():
                    if mac_addr not in self._rc_stations.keys():
                        self._rc_stations.update({mac_addr: station})
                        self._loop.create_task(
                            self.set_rate(station),
                            name=f"rate_setter_{station.mac_addr}",
                        )
            except (KeyboardInterrupt, OSError, IOError, asyncio.CancelledError):
                break

    async def set_rate(self, station):
        rate_choices = self._multi_rate_retry.split(";")[0].split(",")
        counts = self._multi_rate_retry.split(";")[1].split(",")

        supp_rates = station.supp_rates
        rate_idx = 0
        airtimes_ns = copy.deepcopy(station.airtimes_ns)
        airtimes_ns.sort()
        fastest_airtime = airtimes_ns[0]

        while True:
            rates = []
            try:
                for rate_choice in rate_choices:
                    if rate_choice == "random":
                        rates.append(random.choice(station.supp_rates))
                    elif rate_choice == "lowest":
                        rates.append(station.supp_rates[0])
                    elif rate_choice == "fastest":
                        rates.append(station.supp_rates[-1])
                    elif rate_choice == "round_robin":
                        rates.append(supp_rates[rate_idx])
                        rate_idx += 1
                        if rate_idx == len(supp_rates):
                            rate_idx = 0

                first_rate = rates[0]

                airtime_first_rate = station.airtimes_ns[
                    station.supp_rates.index(first_rate)
                ]
                weight = airtime_first_rate / fastest_airtime

                self._logger.debug(
                    f"{self._ap.name}:{station.radio}:{station.mac_addr}: Setting {rates} for {self._interval_ns*weight*1e-6:.3f} ms"
                )

                start_time = time.perf_counter_ns()
                while True:
                    self._ap.set_rate(station.radio, station.mac_addr, rates, counts)
                    if (
                        time.perf_counter_ns() - start_time
                    ) > self._interval_ns * weight:
                        break
                    await asyncio.sleep(0.01)

            except (KeyboardInterrupt, OSError, IOError, asyncio.CancelledError):
                break


async def start(ap, radio, **options):
    rate_setter = ManualMRRSetter(ap, radio, **options)
    await asyncio.sleep(0.1)
    await rate_setter.execute_rate_setting()
