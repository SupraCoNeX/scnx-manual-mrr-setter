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

=======
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
	  * ``round_robin``: Select a consecutive rate out of the all rates supported by the station in a
	  round robin manner.
	  * ``rate-idx``: Select a known fixed rate index that belongs to the set of rates supported by the station.
	  This index is required to be in the format defined by the ORCA < add link >

2. ``update_interval_ns``
	Update interval defines the time duration for which a give MRR setting use applied.
	This value is providing in nano seconds unit.


Examples
--------

1. options = ``{"multi_rate_retry":"lowest;1"}`` will set the MRR with the lowest supported rate with count 1.
Update interval used is 10e6 ns.
2. options = ``{"multi_rate_retry":"random,lowest;4,1"}`` will set a randomly chosen rate in the first MRR stage
and the lowest supported rate in the second, with counts 4 and 1 respectively. Update interval used is 10e6 ns.
3. options = ``{"multi_rate_retry":"round_robin, highest;5,2"}`` will set consecutive rates the first MRR stage
from the set of supported rated in a round-robin manner with count 5, while the second stage is set with the highest
supported rate with count 2. Update interval used is 10e6 ns.
4. options = ``{"update_interval_ns":50e6}`` will set a randomly chosen rate in the first MRR stage with count 1.
Update interval used is 50e6 ns.


"""

import asyncio
import time
import random
import copy
import logging
import rateman
from .rate_table import RateStatistics

__all__ = ["configure", "run"]

def _parse_mrr(mrr: str, control_type) -> (list, list):
    """Parse MRR options.

    User-defined MRR options are parsed to provide lists of rates and counts.

    Parameters
    ----------
    mrr: str
        Format `rate-idx-1, rate-idx-2, ..., rate-idx-max_mrr_stage; count-1, count-2, ..., count-max_mrr_stage`.
        Note: len(rates) == len(counts)

    control_type: str
        Type of control (e.g., "tpc")

    Returns
    -------
    rates: list
        Rate per MRR stage
    counts: list
        Maximum retry count per MRR stage

    """

    rate_part, count_part, *txpower_part = mrr.split(";")

    if control_type == "tpc":
        txpowers = txpower_part[0].split(",")
        if len(txpower_part) > 1:
            raise ValueError("Too many parts in MRR string for 'tpc' control_type")
    else:
        txpowers = []

    rates = rate_part.split(",")
    counts = [int(cnt, 16) for cnt in count_part.split(",")]

    if len(rates) != len(counts):
        raise ValueError("Rates and counts must have the same length")

    return rates, counts, txpowers


async def configure(sta: rateman.Station, **options: dict):
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

    airtimes = sorted([sta.accesspoint.get_rate_info(rate)[0] for rate in sta.supported_rates])
    interval = options.get("update_interval_ns", 10_000_000)
    control_type = options.get("control_type", "rc")
    save_statistics = options.get("save_stats", False)

    rates, counts, txpowers = _parse_mrr(
        options.get("multi_rate_retry", "random;1"), control_type
    )
    log = sta.log

    await sta.set_manual_rc_mode(True)
    if control_type == "tpc":
        await sta.set_manual_tpc_mode(True)
    else:
        await sta.set_manual_tpc_mode(False)

    await sta.reset_kernel_rate_stats()
    sta.reset_rate_stats()

    if save_statistics:
        rate_table = RateStatistics(sta, options.get("data_dir", "."))
    else:
        rate_table = RateStatistics(sta)

    return (
        sta,
        control_type,
        airtimes,
        interval,
        (rates, counts, txpowers),
        log,
        rate_table,
    )


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
    (
        sta,
        control_type,
        airtimes,
        interval,
        (rates, counts, txpowers),
        log,
        rate_table,
    ) = args
    supported_rates = sta.supported_rates
    supported_txpowers = sta.accesspoint.txpowers(sta.radio)
    idx_txpower = 0
    idx_rate = 0

    log.info(
        f"{sta.accesspoint.name}:{sta.radio}:{sta.mac_addr}: Start manual MRR setter"
    )

    while True:
        try:
            mrr_rates = []
            mrr_txpowers = []

            for mrr_stage, r in enumerate(rates):
                if r == "random":
                    mrr_rates.append(random.choice(supported_rates))
                elif r == "slowest":
                    mrr_rates.append(supported_rates[0])
                elif r == "fastest":
                    mrr_rates.append(supported_rates[-1])
                elif r in supported_rates:
                    mrr_rates.append(r)

                if control_type == "tpc":
                    if txpowers[mrr_stage] == "random":
                        mrr_txpowers.append(random.choice(supported_txpowers))
                    elif txpowers[mrr_stage] == "slowest":
                        mrr_txpowers.append(supported_txpowers[0])
                    elif txpowers[mrr_stage] == "highest":
                        mrr_txpowers.append(supported_txpowers[-1])
                    elif txpowers[mrr_stage] == "round_robin":
                        mrr_txpowers.append(supported_txpowers[idx_txpower])
                        idx_txpower = (idx_txpower + 1) % len(supported_txpowers)
                    elif float(txpowers[mrr_stage]) in supported_txpowers:
                        mrr_txpowers.append(float(txpowers[mrr_stage]))

                if r == "round_robin":
                    mrr_rates.append(supported_rates[idx_rate])
                    if control_type == "tpc":
                        if txpowers[mrr_stage] != "round_robin":
                            idx_rate = (idx_rate + 1) % len(supported_rates)
                        elif txpowers[mrr_stage] == "round_robin" and idx_txpower == 0:
                            idx_rate = (idx_rate + 1) % len(supported_rates)
                    else:
                        idx_rate = (idx_rate + 1) % len(supported_rates)

            first_airtime = sta.accesspoint.get_rate_info(mrr_rates[0])[0]
            weight = first_airtime / airtimes[0]

            if control_type == "tpc":
                log.debug(
                    "%(ap)s:%(phy)s:%(mac)s: Setting rates=[%(r)s] counts=[%(c)s] txpowers=[%(t)s]"
                    % dict(
                        ap=sta.accesspoint.name,
                        phy=sta.radio,
                        mac=sta.mac_addr,
                        r=",".join([f"{r:x}" for r in mrr_rates]),
                        c=",".join([f"{c:x}" for c in counts]),
                        t=",".join([f"{c:x}" for t in txpowers])
                    ) + f"for {interval * weight * 1e-6:.3f} ms."
                )
            else:
                log.debug(
                    "%(ap)s:%(phy)s:%(mac)s: Setting rates=[%(r)s] counts=[%(c)s] for %(dur).3f"
                    % dict(
                        ap=sta.accesspoint.name,
                        phy=sta.radio,
                        mac=sta.mac_addr,
                        r=",".join([f"{r:x}" for r in mrr_rates]),
                        c=",".join([f"{c:x}" for c in counts]),
                        dur=interval * weight * 1e-6
                    )
                )

            start_time = time.perf_counter_ns()

            if control_type == "tpc":
                await sta.set_rates_and_power(mrr_rates, counts, mrr_txpowers)
            else:
                await sta.set_rates(mrr_rates, counts)

            await asyncio.sleep(0)

            while time.perf_counter_ns() - start_time < interval * weight:
                await asyncio.sleep(0.001)

            rate_table.update(sta)

        except asyncio.CancelledError:
            if rate_table.save_statistics:
                rate_table._output_file.close()
            break
