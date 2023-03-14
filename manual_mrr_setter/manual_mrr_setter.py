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
	def __init__(self, ap, sta, logger=None, **options):
		self._ap = ap
		self._sta=sta
		self._radio = sta.radio
		self._update_interval_ns = options.get("update_interval_ns", 10e6)
		self._multi_rate_retry = options.get("multi_rate_retry", "random;1")
		self._logger = logger if logger else logging.getLogger()
		self._logger.info(f"{self._ap.name}:{self._radio}: Starting Manual MRR Setter")
		print(f"{self._ap.name}:{self._radio}: Starting Manual MRR Setter")

	async def set_rate(self):
		station=self._sta
		rate_choices = self._multi_rate_retry.split(";")[0].split(",")
		counts = self._multi_rate_retry.split(";")[1].split(",")
		supp_rates = station.supp_rates
		rate_idx = 0
		airtimes_ns = copy.deepcopy(station.airtimes_ns)
		airtimes_ns.sort()
		fastest_airtime = airtimes_ns[0]

		# print(
		# 	f"Radio {station.radio}, Station {station.mac_addr}: Supported rates {station.supp_rates}"
		# )
		while True:
			await asyncio.sleep(0.1)
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

				airtime_first_rate = station.airtimes_ns[
					station.supp_rates.index(rates[0])
				]
				weight = airtime_first_rate / fastest_airtime

				self._logger.warning(
					f"{self._ap.name}:{station.radio}:{station.mac_addr}: Setting {rates} for {self._update_interval_ns*weight*1e-6:.3f} ms"
				)
				start_time = time.perf_counter_ns()
				self._ap.set_rate(station.radio,station.mac_addr,rates,counts)
				while True:
					if (
							time.perf_counter_ns() - start_time
					) > self._update_interval_ns * weight:
						# print(
						# 	f"Radio {station.radio}, Station {station.mac_addr}: Counts {station.stats}"
						# )
						break
			except (KeyboardInterrupt, OSError, IOError, asyncio.CancelledError):
				break


async def start(ap, sta, logger=None, **options):
	rate_controller = ManualMRRSetter(ap, sta, logger, **options)
	await asyncio.sleep(0.1)
	await rate_controller.set_rate()
