# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import asyncio
import time
import random
import logging
import copy

__all__ = [ "start" ]

def _parse_mrr(mrr):
	r,c = mrr.split(";")
	rates = r.split(",")
	counts = [int(cnt, 16) for cnt in c.split(",")]

	if len(rates) != len(counts):
		raise ValueError("rates and counts must have the same length")

	return rates, counts

async def start(ap, sta, logger=None, **options):
	airtimes = copy.deepcopy(sta.airtimes_ns)
	airtimes.sort()
	interval = options.get("update_interval_ns", 10_000_000)
	rates, counts = _parse_mrr(options.get("multi_rate_retry", "random;1"))
	log = logger if logger else logging.getLogger()

	idx = 0

	log.debug(f"{ap.name}:{sta.radio}:{sta.mac_addr}: Start manual MRR setter")

	while True:
		mrr_rates = []
		try:
			for r in rates:
				if r == "random":
					mrr_rates.append(random.choice(sta.supp_rates))
				elif r == "lowest":
					mrr_rates.append(sta.supp_rates[0])
				elif r == "fastest":
					mrr_rates.append(sta.supp_rates[-1])
				elif r == "round_robin":
					mrr_rates.append(sta.supp_rates[idx])
					idx += 1
					if idx == len(sta.supp_rates):
						idx = 0
				else:
					raise ValueError(f"unknown rate designation: {r}")

			first_airtime = sta.airtimes_ns[sta.supp_rates.index(mrr_rates[0])]
			weight = first_airtime / airtimes[0]

			log.info(
				f"{ap.name}:{sta.radio}:{sta.mac_addr}: Setting {mrr_rates} "
				f"for {interval * weight * 1e-6:.3f} ms"
			)

			start_time = time.perf_counter_ns()
			ap.set_rate(sta.radio, sta.mac_addr, mrr_rates, counts)

			await asyncio.sleep(0) # make sure to always yield at least once

			while time.perf_counter_ns() - start_time < interval * weight:
				await asyncio.sleep(0)
		except (KeyboardInterrupt, OSError, IOError, asyncio.CancelledError):
			break
