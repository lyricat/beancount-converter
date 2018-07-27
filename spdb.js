var fs = require('fs')
var loadCSV = function (filename) {
	/* spec
	2018-05-25	2018-05-25	支付宝-上海新语餐饮管理有限公司	28.89	6592	主卡
	2018-05-25	2018-05-25	支付宝-消费-滴滴出行科技有限公司	29.51	6592	主卡
	2018-05-25	2018-05-25	支付宝-消费-天津舒行科技有限公司	145.00	6592	主卡
	*/
	var input = fs.readFileSync(filename).toString('utf8')
	var lines = input.split('\n');
	var records = [];
	
	for (var i = 0; i < lines.length; i ++) {
		var parts = lines[i].split('\t').filter(function (x) { return x && x.trim().length !== 0; });
		if (parts.length !== 0) {
			var amount = parts[3][0] === '-' ? parts[3].substring(1): parts[3];
			amount = amount.replace(',', '');
			var direction = parts[3][0] === '-' ? 1: 0;
			records.push({
				time: parts[0],
				description: parts[2],
				amount: amount,
				direction: direction,
			});
		}
	}
	return records
}

var autoProc = function (record) {
	var mapping = require('./mapping.json')
	for (var i = 0; i < mapping.length; i += 1) {
		if (record.description.indexOf(mapping[i][0]) !== -1) {
			return (
`${record.time} * "${record.description}" "${mapping[i][1]}"
    Liabilities:SPDB:CreditCards   -${record.amount} CNY
    ${mapping[i][2]}               +${record.amount} CNY
`);
		}
	}
	return (
`${record.time} * "${record.description}" "备注"
    Liabilities:SPDB:CreditCards   -${record.amount} CNY
    Expenses:Unknown               +${record.amount} CNY
`
	);
}

var printResult = function (records) {
	for (var i = 0; i < records.length; i ++) {
		if (records[i].direction) {
			console.log(
`${records[i].time} * "${records[i].description}" "备注"
    Assets:Unknown                 -${records[i].amount} CNY
    Liabilities:SPDB:CreditCards   +${records[i].amount} CNY
`)
		} else {
			console.log(autoProc(records[i]));
		}
	}
}

var record = loadCSV('./input.txt')
printResult(record)
