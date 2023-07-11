# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

"""SCNX Manual MRR Setter

This module contains the functions required to set the Multi-Rate-Retry (MRR)
chain for the transmission of frame based on the ORCA toolset. 
A controller device uses a `rateman.RateMan` object to annotate rates
and counts of the MRR via the Manual-MRR-Setter. Generally, resource control
algorithm derive statistics based on which resource control decisions are
performed. Direct setting the rates and counts without any analysis of
statistics is implied by the term 'manual' in the naming of this package.

Example
-------
	To be added

Notes
-----
	To be added

"""

import asyncio
import time
import random
import logging
import copy

import rateman

__all__ = ["configure", "run"]


def _parse_mrr(mrr: str) -> (list, list):
	"""Parse MRR options.

	User defined MRR options are parsed to provide lists
	rates and counts.

	Parameters
	----------
	mrr: str
		Format `rate-idx-1, rate-idx-2,...,rate-idx-max_mrr_stage; count-1, count-2,...,count-max_mrr_stage`.
		Note: len(rates_opts) == len(counts)

	Returns
	-------
	rates: list
		Rate per MRR stage
	counts: list
		Maximum retry count per MRR stage

	"""

	r,c = mrr.split(";")
	rates = r.split(",")
	counts = [int(cnt, 16) for cnt in c.split(",")]

	if len(rates) != len(counts):
		raise ValueError("rates and counts must have the same length")

	return rates, counts


async def configure(sta: rateman.Station, **options: dict):
	sta.set_manual_rc_mode(True)
	sta.set_manual_tpc_mode(False)

	airtimes = copy.deepcopy(sta.airtimes_ns)
	airtimes.sort()
	interval = options.get("update_interval_ns", 10_000_000)
	rates, counts = _parse_mrr(options.get("multi_rate_retry", "random;1"))
	log = sta._log

	return (sta, airtimes, interval, (rates, counts), log)


async def run(args):
	sta = args[0]
	airtimes = args[1]
	interval = args[2]
	rates, counts = args[3][0], args[3][1]
	log = args[4]

	idx = 0
	log.info(f"{sta.accesspoint.name}:{sta.radio}:{sta.mac_addr}: Start manual MRR setter")

	while True:
		mrr_rates = []
		try:
			for r in rates:
				match r:
					case "random":
						mrr_rates.append(random.choice(sta.supported_rates))
					case "lowest":
						mrr_rates.append(sta.supported_rates[0])
					case "fastest":
						mrr_rates.append(sta.supported_rates[-1])
					case "round_robin":
						mrr_rates.append(sta.supported_rates[idx])
						idx += 1
						if idx == len(sta.supported_rates):
							idx = 0
					case _:
						raise ValueError(f"unknown rate designation: {r}")

			first_airtime = sta.airtimes_ns[sta.supported_rates.index(mrr_rates[0])]
			weight = first_airtime / airtimes[0]

			log.debug(
				f"{sta.accesspoint.name}:{sta.radio}:{sta.mac_addr}: Setting {mrr_rates} "
				f"for {interval * weight * 1e-6:.3f} ms"
			)

			start_time = time.perf_counter_ns()
			sta.set_rates(mrr_rates, counts)

			await asyncio.sleep(0) # make sure to always yield at least once

			while time.perf_counter_ns() - start_time < interval * weight:
				await asyncio.sleep(0)
		except asyncio.CancelledError:
			break
