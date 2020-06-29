# beancount-converter
A conversor to process csv file from bank to `.bean` file.

## Run

1. fill your csv to input.txt
2. run `./proc.py -m MODE -f input_file > output.txt`

## Modes

- spdb: load and parse transactions from [浦东发展银行](https://ebill.spdbccc.com.cn/cloudbank-portal/myBillController/showIndex.action)
- cmb: load and parse transactions from 招商银行, you may use https://tabula.technology to extract them from table of PDF.
- futu: load and parse trading history from [富途证券](https://trade-history.futu5.com/)
