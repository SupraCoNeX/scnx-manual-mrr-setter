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

**Rate Control Options**

Options for MRR chain setting are described within a dictionary. Default options,

.. code-block:: sh

	multi_rate_retry: 'random;1'
	update_interval_ns: 10_000_000

1. ``multi_rate_retry``
	Per MRR stage the rate and count options can be specific using this option.

	**rate options per MRR stage**
	  * ``lowest``: Select the lowest theoretical throughput rate supported by the station.
	  * ``fastest``: Select the highest theoretical throughput rate supported by the station.
	  * ``random``: Select a random rate out of the all rates supported by the station.
	  * ``round_robin``: Select a consecutive rate out of the all rates supported by the station in a round robin manner.
	  * ``rate-idx``: Select a known fixed rate index that belongs to the set of rates supported by the station. This index is required to be in the format defined by the ORCA < add link >

2. ``update_interval_ns``
	Update interval defines the time duration for which a give MRR setting use applied. This value is providing in nano seconds unit.


Examples
--------

1. options = ``{"multi_rate_retry":"lowest;1"}`` will set the MRR with the lowest supported rate with count 1. Update interval used is 10e6 ns.
2. options = ``{"multi_rate_retry":"random,lowest;4,1"}`` will set a randomly chosen rate in the first MRR stage and the lowest supported rate in the second, with counts 4 and 1 respectively. Update interval used is 10e6 ns.
3. options = ``{"multi_rate_retry":"round_robin, highest;5,2"}`` will set consecutive rates the first MRR stage from the set of supported rated in a round robin manner with count 5, while the second stage is set with the highest supported rate with count 2. Update interval used is 10e6 ns.
4. options = ``{"update_interval_ns":50e6}`` will set a randomly chosen rate in the first MRR stage with count 1. Update interval used is 50e6 ns.



"""

import asyncio
import time
import random
import copy
import logging
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
<<<<<<< HEAD
	await sta.set_manual_rc_mode(True)
	await sta.set_manual_tpc_mode(False)
=======
	"""
	Configure station to perform manual MRR chain setting. <Actual configuration steps>

	Parameters
	----------
	sta: rateman.Station
		Station object based on rateman abstraction.
	options: dict
		MRR chain setting options list in module description.

	Returns
	-------
	sta: rateman.Station
	airtimes: list
		Transmission airtimes in nanosecond for MCS data supported by station, sorted in ascending order.
	interval: int
		Update interval for setting a given MRR chain in nanosecond.
	(rates, counts): tuple
		Rate options and their corresponding counts to be used MRR chain setting.
	log: logging.Logger
		For logging MRR setting events.

	"""

	sta.set_manual_rc_mode(True)
	sta.set_manual_tpc_mode(False)
>>>>>>> 6eaa75e (draft documentation)

	airtimes = copy.deepcopy(sta.airtimes_ns)
	airtimes.sort()
	interval = options.get("update_interval_ns", 10_000_000)
	rates, counts = _parse_mrr(options.get("multi_rate_retry", "random;1"))
	log = sta._log

	return sta, airtimes, interval, (rates, counts), log


async def run(args):
	"""
	Run Manual MRR Setter.

	Parameters
	----------
	args: dict
		Returned from manual_mrr_setter.configure().

	Returns
	-------

	"""
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
			await sta.set_rates(mrr_rates, counts)

			await asyncio.sleep(0) # make sure to always yield at least once

			while time.perf_counter_ns() - start_time < interval * weight:
				await asyncio.sleep(0)
		except asyncio.CancelledError:
			break
