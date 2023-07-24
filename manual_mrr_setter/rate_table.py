# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

"""Manual MRR Setter Rate Table

This module contains functions to derive a table of statistics for rate and power used for packet transmission.
"""
__all__ = ['RateStatistics']


class RateStatistics:
	def __init__(self):
		self._stats = dict
		self._last_seen = dict

		pass

	@property
	def cur_stats(self, rate="all"):
		if rate not in self._stats:
			raise KeyError
		elif rate in self._stats:
			return self._stats[rate][self._last_seen[rate]]
		return 1

	@property
	def hist_stats(self):
		return 1

	def update(self, new_stats: dict):
		if new_stats['rate'] in self._stats:
			a=1
		else:
			b=1

	def get_table(self):
		pass
