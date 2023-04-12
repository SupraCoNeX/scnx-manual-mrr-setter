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

__all__ = ["start"]


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
    rates_opts: list
        Rate options per MRR stage
    counts: list
        Maximum retry counts per MRR stage

    """
    r, c = mrr.split(";")
    rates_opts = r.split(",")
    counts = [int(cnt, 16) for cnt in c.split(",")]

    if len(rates_opts) != len(counts):
        raise ValueError("rates and counts must have the same length")

    return rates_opts, counts


async def start(
    ap: rateman.AccessPoint, sta: rateman.Station, logger=None, **options: dict
):
    """Manual-MRR-Setter Start.

    This is the main asyncio function that deals with parsing MRR options as well as the update interval,
    and setting of MRR chain per update interval.

    Parameters
    ----------
    ap: rateman.AccessPoint
    sta: rateman.Station
    logger: logging.Logger
    options: dict

    Returns
    -------
        Nothing is returned. The function runs until terminated via RateMan externally.

    """
    airtimes = copy.deepcopy(sta.airtimes_ns)
    airtimes.sort()
    interval = options.get("update_interval_ns", 10_000_000)
    rates_opts, counts = _parse_mrr(options.get("multi_rate_retry", "random;1"))
    log = logger if logger else logging.getLogger()
    rates_iter = [iter(sta.supp_rates) for _ in range(len(rates_opts))]
    log.debug(f"{ap.name}:{sta.radio}:{sta.mac_addr}: Start manual MRR setter")

    while True:
        rates = []
        try:
            for mrr_stage, r in enumerate(rates_opts):
                if r == "random":
                    rates.append(random.choice(sta.supp_rates))
                elif r == "lowest":
                    rates.append(sta.supp_rates[0])
                elif r == "highest":
                    rates.append(sta.supp_rates[-1])
                elif r in sta.supp_rates:
                    rates.append(rates[mrr_stage])
                elif r == "round_robin":
                    try:
                        next_rate = next(rates_iter[mrr_stage])
                    except StopIteration:
                        rates_iter[mrr_stage] = iter(sta.supp_rates)
                        next_rate = next(rates_iter[mrr_stage])
                    rates.append(next_rate)
                else:
                    raise ValueError(f"unknown rate designation: {r}")

            first_airtime = sta.airtimes_ns[sta.supp_rates.index(rates[0])]
            weight = first_airtime / airtimes[0]

            log.info(
                f"{ap.name}:{sta.radio}:{sta.mac_addr}: Setting {rates} "
                f"for {interval*weight*1e-6:.3f} ms"
            )

            await asyncio.sleep(0)
            start_time = time.perf_counter_ns()
            ap.set_rate(sta.radio, sta.mac_addr, rates, counts)
            while time.perf_counter_ns() - start_time < interval * weight:
                await asyncio.sleep(0)
        except (KeyboardInterrupt, OSError, IOError, asyncio.CancelledError):
            break
