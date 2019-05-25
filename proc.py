#! /usr/bin/env python
# coding: UTF-8

import json
import argparse
import csv
import datetime
import os
import io
import sys
from os import path
import locale

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8') 

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

parser = argparse.ArgumentParser()
parser.add_argument("-m", "--mode", dest="mode", help="mode. spdb, cmb, futu", metavar="LOCAL")
parser.add_argument("-f", "--file", dest="file", help="input file, json or csv", metavar="LOCAL")
options = parser.parse_args()

with open(path.join(sys.path[0], 'config.json'), encoding="UTF-8") as fd:
    conf = json.loads(fd.read())

COMM_EXP_TMPL = """%s * %s
    Liabilities:%s   -%s CNY
    %s                 +%s CNY
"""

COMM_EXP_UNKNOWN_TMPL = """%s * %s
    Liabilities:%s               -%s CNY
    Expenses:Unknown               +%s CNY
"""

COMM_REFUND_TMPL = """%s * %s
    Assets:Unknown                 -%s CNY
    Liabilities:%s               +%s CNY
"""

US_BUY_TMPL = """%s * "%s" #%s_SHARE
    Assets:Futu
    Assets:Futu                    +%d %s_SHARE @ %s USD
    Expenses:Commission            +5 USD
%s price %s_SHARE   %s USD
"""

US_SELL_TMPL = """%s * "%s" #%s_SHARE
    Assets:Futu                    -%d %s_SHARE @ %s USD
    Assets:Futu                    
    Expenses:Commission            +5 USD
%s price %s_SHARE   %s USD
"""

US_SHORT_TMPL = """%s * "%s" #%s_SHARE
    Liabilities:Futu               -%s %s_SHARE @ %s USD
    Assets:Futu                    
    Expenses:Commission            +5 USD
%s price %s_SHARE   %s USD
"""

US_SHORT_CLOSE_TMPL = """%s * "%s" #%s_SHARE
    Assets:Futu                    
    Liabilities:Futu               +%s %s_SHARE @ %s USD
    Expenses:Commission            +5 USD
%s price %s_SHARE   %s USD
"""

def load_json(filename):
    fd = open(filename, 'r', encoding="UTF-8")
    data = fd.read()
    js = json.loads(data)
    fd.close()
    return js

def load_csv(filename, is_strip_head=False):
    fd = open(filename, 'r', encoding="UTF-8")
    csv_reader = csv.reader(fd, delimiter=',')
    records = []
    for row in csv_reader:
        records.append(tuple(row))
    return records[1:] if is_strip_head else records

def load_spdb(filename):
    """
    Download XLS from https://ebill.spdbccc.com.cn/cloudbank-portal/myBillController/showIndex.action
    and export as CSV
    """
    return load_csv(filename, is_strip_head=True)

def load_cmb(filename):
    """
    Using https://tabula.technology to extract table from PDF.
    and export as CSV
    """
    return load_csv(filename, is_strip_head=True)

def load_futu(filename):
    """
    Extract data from https://my.futu5.com/account/history?ltype=2
    choose "成交记录"
    and export as CSV
    """
    return load_csv(filename)

def build_records_spdb_legacy(mapping, record):
    for entry in mapping:
        if record['description'].upper().find(entry[0].upper()) != -1:
            return COMM_EXP_TMPL % (record['time'], record['description'] + ', ' + entry[1], conf['LB_SPDB_NAME'], record['amount'], entry[2], record['amount'])
    return COMM_EXP_UNKNOWN_TMPL % (record['time'], record['description'], conf['LB_SPDB_NAME'], record['amount'], record['amount'])

def build_records_spdb(mapping, record):
    def recipient_and_desc(recip, desc):
        return '"%s" "%s"' % (recip, desc) if recip else '"%s"' % desc

    time, _, description, card_no, _, _, amount = record
    time = datetime.datetime.strptime(time, "%Y%m%d")
    space_pos = description.find(' ')
    recipient = ''
    if space_pos != -1:
        recipient = description[:space_pos]
        description = description[space_pos + 1:]
    amount = locale.atof(amount)
    is_refund = True if amount < 0 else False
    abs_amount = abs(amount)
    time = time.strftime('%Y-%m-%d')
    if is_refund:
        return COMM_REFUND_TMPL % (time, recipient_and_desc(recipient, description), abs_amount, conf['LB_SPDB_NAME'], abs_amount)
    else:
        for entry in mapping:
            if description.upper().find(entry[0].upper()) != -1:
                return COMM_EXP_TMPL % (time, recipient_and_desc(recipient, '%s, %s' % (description, entry[1])), conf['LB_SPDB_NAME'], abs_amount, entry[2], abs_amount)
        return COMM_EXP_UNKNOWN_TMPL % (time, recipient_and_desc(recipient, description), conf['LB_SPDB_NAME'], abs_amount, abs_amount)

def build_records_cmb(mapping, record):
    def recipient_and_desc(recip, desc):
        return '"%s" "%s"' % (recip, desc) if recip else '"%s"' % desc

    time, _, description, amount, card_no, _, _ = record
    time = '0' + time
    time = datetime.datetime.strptime(time, "%m%d")
    time = time.replace(year=2019)
    sep_pos = description.find('-')
    recipient = ''
    if sep_pos != -1:
        recipient = description[:sep_pos]
        description = description[sep_pos + 1:]
    amount = locale.atof(amount)
    is_refund = True if amount < 0 else False
    abs_amount = abs(amount)
    time = time.strftime('%Y-%m-%d')
    if is_refund:
        return COMM_REFUND_TMPL % (time, recipient_and_desc(recipient, description), abs_amount, conf['LB_CMB_NAME'], abs_amount)
    else:
        for entry in mapping:
            if description.upper().find(entry[0].upper()) != -1:
                return COMM_EXP_TMPL % (time, recipient_and_desc(recipient, '%s, %s' % (description, entry[1])), conf['LB_CMB_NAME'], abs_amount, entry[2], abs_amount)
        return COMM_EXP_UNKNOWN_TMPL % (time, recipient_and_desc(recipient, description), conf['LB_CMB_NAME'], abs_amount, abs_amount)

def build_records_futu(record):
    dr, sym, name, price, amount, time = record
    time = datetime.datetime.strptime(time, "%Y/%m/%d %H:%M:%S")
    price = float(price)
    amount = int(amount)
    time = time.strftime('%Y-%m-%d')
    if dr == '卖出':
        return US_SELL_TMPL % (time, dr + ' ' + sym, sym, amount, sym, price, time, sym, price)
    elif dr == '买入':
        return US_BUY_TMPL % (time, dr + ' ' + sym, sym, amount, sym, price, time, sym, price)
    elif dr == '卖空':
        return US_SHORT_TMPL  % (time, dr + ' ' + sym, sym, amount, sym, price, time, sym, price)
    else: # 平仓
        return US_SHORT_CLOSE_TMPL % (time, dr + ' ' + sym, sym, amount, sym, price, time, sym, price)

def print_spdb_legacy(mapping, records):
    # 废弃不再使用
    for record in records:
        if record['direction']:
            print(COMM_REFUND_TMPL % (record['time'], record['description'], record['amount'], conf['LB_SPDB_NAME'], record['amount']))
        else:
            print(build_records_spdb_legacy(mapping, record))

def print_futu(records):
    for record in records:
        print(build_records_futu(record))

def print_spdb(mapping, records):
    for record in records:
        print(build_records_spdb(mapping, record))

def print_cmb(mapping, records):
    for record in records:
        ret = build_records_cmb(mapping, record)
        locale.setlocale(locale.LC_ALL, '')
        # print(locale.getlocale())
        print(ret)

if __name__ == '__main__':
    mapping = load_json(path.join(os.path.dirname(os.path.realpath(__file__)), 'mapping.json'))
    if options.mode == 'spdb':
        records = load_spdb(options.file)
        print_spdb(mapping, records)
    elif options.mode == 'cmb':
        records = load_cmb(options.file)
        print_cmb(mapping, records)
    elif options.mode == 'futu':
        records = load_futu(options.file)
        print_futu(records)

