import asyncio
import argparse
import re
import statistics

from contextlib import suppress
from statistics import mean
from paramiko import SSHClient

class MonitorInterface:
    def __init__(self, sta, namespace: str, interface: str, interval: str):
        self._sta = sta
        self._ap = sta.accesspoint
        self._namespace = namespace
        self._interface = interface
        self._interval = interval

        self._loop = self._ap.loop
        #self._ap_client = self.connect('172.24.23.34', 'root')
        #self._sta_client = self.connect('172.24.23.35', 'root')
        self._process = None

        self._throughput_meas = []
        self._curr_rate = None

        self._mon_task = self._loop.create_task(self.start_tcpdump())
        self._signal_task = self._loop.create_task(self.start_signal_mon())

    @property
    def loop(self):
        return self._loop

    def reset_measurement(self):
        self._throughput_meas.clear()

    @property
    def curr_rate(self):
        return self._curr_rate

    @curr_rate.setter
    def curr_rate(self, rate):
        self._curr_rate = rate

    @property
    def avg_throughput(self):
        try:
            return mean(self._throughput_meas)
        except statistics.StatisticsError:
            return 0

    def get_throughput_measurements(self):
        return self._throughput_meas

    def calculate_average_ampdu_len(self):
        ampdu_len = self._sta.ampdu_subframes
        ampdu_packets = self._sta.ampdu_aggregates

        avg_ampdu = ampdu_len / ampdu_packets
        self._sta.reset_ampdu_stats()
        return avg_ampdu


    def connect(self, ip_addr, username):
        client = SSHClient()
        client.load_system_host_keys()
        client.connect(ip_addr, username=username)

        return client

    def extract_noise(self, client, interface):
        stdin, stdout, stderr = client.exec_command(f'iwinfo {interface} info | grep "Noise" | sed "s/.*Noise: //; s/ dBm//"')
        output = stdout.read().decode().strip()

        if output:
            noise = float(output)
            return f"{round(noise, 1)}"

    async def start_signal_mon(self):
        while True:
            try:
                if self._curr_rate:
                    #data = self.extract_noise(self._ap_client, "phy0-mesh0")
                    #self._ap.rcd_trace_file.write(f"phy0;ap;noise;{data}\n")

                    #data = self.extract_noise(self._sta_client, "phy0-mesh0")
                    #self._ap.rcd_trace_file.write(f"phy0;sta;noise;{data}\n")

                    attempts, successes, timestamp = self._sta.get_rate_stats(self._curr_rate)
                    if attempts:
                        succ_prob = successes / attempts
                        self._ap.rcd_trace_file.write(f"phy0;stats;{self._curr_rate};{round(succ_prob, 2)};{successes};{attempts}\n")
                        self._sta.reset_rate_stats()

                await asyncio.sleep(0.1)
            except asyncio.CancelledError as e:
                raise e

    async def start_bmon(self):
        cmd = [
            "sudo",
            "ip",
            "netns",
            "exec",
            self._namespace,
            "bmon",
            "-o",
            "format:fmt=$(attr:rxrate:bytes)\n",
            "-p",
            self._interface,
            "-r",
            self._interval,
        ]
        self._process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)

        try:
            while True:
                line = await self._process.stdout.readline()
                if self._curr_rate:
                    self._throughput_meas.append((float(line.decode().strip()) * 8) / 10**6)
        except asyncio.CancelledError as e:
            self._process.terminate()
            await self._process.wait()
            raise e

    async def start_tcpdump(self):
        command = [
                'sudo', 'ip', 'netns', 'exec', self._namespace, 'tcpdump', '-i', self._interface, '-nes', '150'
            ]

        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE
        )

        bytes_count = 0
        last_time = None

        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break

                match = re.search(r'length (\d+)', line.decode())
                if match:
                    bytes_count += int(match.group(1))

                current_time = asyncio.get_event_loop().time()
                if last_time is None:
                    last_time = current_time

                if current_time - last_time >= 1.0:
                    mbps = round((bytes_count * 8) / 1e6, 2)
                    self._throughput_meas.append(mbps)
                    last_time = current_time
                    bytes_count = 0
        except asyncio.CancelledError as e:
            proc.terminate()
            await proc.wait()
            self._ap.logger.info(f"{self._ap.name}:{self._sta.radio}:{self._sta.mac_addr}:Tcpdump process cancelled.")
            raise e

    async def stop_task(self, task):
        if task and not task.done():
            task.cancel()

            with suppress(asyncio.CancelledError):
                await task
        else:
            self._ap.logger.info(f"{self._ap.name}:{self._sta.radio}:{self._sta.mac_addr}:Task already completed or was None.")

    async def stop(self):
        try:
            async with asyncio.timeout(2):
                await asyncio.gather(
                    self.stop_task(self._mon_task),
                    self.stop_task(self._signal_task),
                )
        except asyncio.TimeoutError:
            self._ap.logger.info(f"{self._ap.name}:{self._sta.radio}:{self._sta.mac_addr}: Task termination timeout!")

        self._mon_task = None
        self._signal_task = None
        self._ap.logger.info(f"{self._ap.name}:{self._sta.radio}:{self._sta.mac_addr}: All monitoring tasks terminated.")