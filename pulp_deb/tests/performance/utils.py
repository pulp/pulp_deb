# coding=utf-8
"""Utilities for testing deb performance"""
import csv

from datetime import datetime


def write_csv_to_tmp(basename, header_row, content_row, add_date=True, dateformat="%d.%m.%y"):
    """Write a CSV file with a header and a single content row to the /tmp/ folder.

    :param basename: The basename of the csv file.
    :param header_row: The column header names.
    :param content_row: The line of data for the content columns.
    :param add_date: Whether the current date should be added to the csv. (default: True).
    :param dateformat: How the date should be formatted (default: %d.%m.%y).
    """
    with open(f"/tmp/{basename}.csv", "w", encoding="UTF-8", newline="") as f:
        writer = csv.writer(f)
        if add_date:
            header_row.insert(0, "date")
            content_row.insert(0, datetime.strftime(datetime.now(), dateformat))
        writer.writerow(header_row)
        writer.writerow(content_row)
