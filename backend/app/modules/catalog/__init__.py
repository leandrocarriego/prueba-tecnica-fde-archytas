"""Catalog: the products the business knows, their current price and its history.

It is the only module that decides what a known product is. It never creates one
by itself from a list: a product it does not know is held back for a person
(RF-07), and a known one that stops appearing keeps its last price (RF-08).
"""
