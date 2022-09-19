# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import asyncio 
import datetime
import time
import os
import random
import csv
import logging

__all__ = [
    "FixRate",
    "start",
]

from .config import (
    rate_setting_interval)

class FixRate:
    def __init__(self, ap, loop, **options):

        self._loop = loop
        self._ap = ap
        self._rc_stations = dict()
        self._rate_setting_interval_ns = options.get("interval_ns", 100)
        self._multi_rate_retry = options.get("multi_rate_retry", "lowest;1")
        self._mcs_dur = dict()
        self.load_rate_mcs_dur()
        
    async def _wait_for_stations(self):
        """
        This async function waits for RateMan to add at least one station and its rate stats.

        """
        while True:
            try:
                if self._ap.get_stations():
                    break
                else:
                    print("Waiting for at least one station!")
                    await asyncio.sleep(self._rate_setting_interval_ns/1e6)
            except KeyboardInterrupt:
                break
        
    async def execute_setting_rates(self):
        """
        Selects rate to fill the MRR chain for the current update interval. Rule
        for selecting the MRR:

        1) First rate in the MRR: Highest Throughput Rate
        2) Second rate in the MRR: Second Highest Throughput Rate
        3) Third rate in the MRR: Maximum Probability Rate

        The MRR is finally set using the set_rate function from AccessPoints object.

        """
        
        print("Starting Random Rate Setter in Userspace")        
        await self._wait_for_stations()
        
        for phy in self._ap.phys:
            self._ap.enable_manual_mode(phy)
            
        while True:
            await asyncio.sleep(1)
            try:
                for mac_addr, station in self._ap.get_stations().items():
                    if mac_addr not in self._rc_stations.keys():
                        self._rc_stations.update({mac_addr: station})
                        
                        self._loop.create_task(self.set_rate_station(station), 
                                            name = f"rate_setter_{station.mac_addr}")
            except KeyboardInterrupt:
                break
    
    async def set_rate_station(self, station):   
        
        airtimes = list(map(self.get_airtime, station.supp_rates))
        airtimes.sort()
        fastest_airtime = airtimes[0]
                    
        while True:
            try:
                rates = [random.choice(station.supp_rates)]
                rates.append(station.supp_rates[0])
                rates.append(station.supp_rates[0])
                rates.append(station.supp_rates[0])
                counts = ["1"] * len(rates)
                start_time = time.perf_counter_ns()
                weight = self.cal_airtime_weight(rates[0], fastest_airtime)
                          
                logging.info(f"Setting {rates[0]} for {self._rate_setting_interval_ns*weight*1e-6} milliseconds")
                while True:
                    self._ap.set_rate(station.radio, station.mac_addr, rates, counts)                    
                    if (time.perf_counter_ns() - start_time) > self._rate_setting_interval_ns*weight:
                        break
                    await asyncio.sleep(0.01)
            except KeyboardInterrupt:
                 break
        
    def cal_airtime_weight(self, rate, fastest_airtime):       
        
        return self.get_airtime(rate)/fastest_airtime
    
    def load_rate_mcs_dur(self):
        """
        Parses the airtimes.csv file which contains information such as airtime, no of
        spatial streams and group type for all MCS Indices currently supported by Min-
        strel RCD. The information is loaded into mcsDur attribute of Minstrel object
        as a dictionary.

        """
        filename = "/home/sankalp/Python_Packages/RateMan/airtimes.csv"

        with open(filename, newline="") as csvfile:
            dataRows = csv.reader(csvfile, delimiter=";")
            for row in dataRows:
                if dataRows.line_num == 1:
                    supp_format = "*;0;#group;index;offset;type;nss;bw;gi;airtime0;airtime1;airtime2;airtime3;airtime4;airtime5;airtime6;airtime7;airtime8;airtime9"
                    line = ";".join(row)
                    if not line == supp_format:
                        raise Exception(
                            "Index to rate conversion file not in supported format!"
                        )
                    continue

                groupIdx = row[3]
                nss = row[6]
                airtimes = row[9:]
                type = row[5]
                airtimes = [airtime for airtime in airtimes if airtime != ""]

                group_info = {"airtimes": airtimes, "type": type, "nss": nss}

                self._mcs_dur.update({groupIdx: group_info})
    
    def get_airtime(self, mcsIdx):
        """
        If a valid MCS index is provided, then it returns the transmission duration, in
        nanoseconds, for the raw data part of an average sized packet using that MCS index.
        Parameters
        ----------
        mcsIdx : str
            Rate Index in Hexadecimal base
        Returns
        -------
        airtime: int
            Transmit duration, in ns, using the provided rate
        """

        groupIdx = mcsIdx[:-1]
        local_offset = int(mcsIdx[-1])
        try:
            group_airtimes = self._mcs_dur[groupIdx]["airtimes"]
            airtime = group_airtimes[local_offset]
            return int(airtime, 16)
        except KeyError:
            print("Provided MCS rate in invalid:", mcsIdx)
    
    
async def start(ap, loop):
    
    fixer = FixRate(ap, loop)
    await asyncio.sleep(0.1)
    await fixer.execute_setting_rates()
    
    