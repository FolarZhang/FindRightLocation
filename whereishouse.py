import requests
import json
import re
import xlwt as xw

limit_time = 80
limit_fee = 20

# 爬虫爬取当前的所有地铁站名
def get_subway():
    subway = set()
    prefix = 'http://bj.bendibao.com'
    home_url = 'http://bj.bendibao.com/ditie/time.shtml'
    strhtml = requests.get(home_url)
    res = r'(?<=<strong><a href=\").+?(?=\")|(?<=<strong><a href=\').+?(?=\')'
    link = re.findall(res, strhtml.text, re.S|re.M)
    for value in link:
        url = prefix + value
        content = requests.get(url)
        res1 = r'(?:shtml" target="_blank">).+?(?:</a></td>)'
        name = re.findall(res1, content.text, re.S|re.M)
        for ele in name:
            ele = ele.lstrip('shtml" target="_blank">')
            ele = ele.rstrip('</a></td>')
            ele = re.sub(u"\\（.*?）", "", ele)
            ele = ele.replace(' ', '')
            if ele[-1] != '站':
                ele = ele + '站'
            subway.add(ele)
    return subway


# 获取参数|地铁站的经纬度
def get_location(addr):
    api_url = f'https://restapi.amap.com/v3/geocode/geo?city=北京市&address={addr}&output=json&key=your_key'
    res = requests.get(api_url)
    json_res = json.loads(res.text)
    if json_res['status'] == '1':
        coords = json_res['geocodes'][0]['location']
    else:
        coords = None
    return coords


# 从stations.txt文件中获取保存的所有地铁站名
def get_subway_fromfile(file):
    subway = set()
    with open(file, 'r') as fp:
        for line in fp:
            line = line.strip('\r\n')
            if len(line) != 0:
                subway.add(line)
    return subway


# 读取coordinate.txt文件中的经纬度信息
def get_coor_fromfile(file):
    ret = dict()
    with open(file, 'r') as fp:
        for line in fp:
            line = line.strip('\r\n')
            if len(line) != 0:
                strs = line.split(': ')
                ret[strs[0]] = strs[1]
    return ret


# 返回查询到的方案中用时小于给定限制的时间和费用
def path_plan(origin, destination, strategy):
    res_list = []
    api_url = f'https://restapi.amap.com/v5/direction/transit/integrated?show_fields=cost&city1=010&city2=010&max_trans=2&origin={origin}&destination={destination}&strategy={strategy}&output=json&key=your_key'
    res = requests.get(api_url)
    json_res = json.loads(res.text)
    if json_res['status'] == '1':
        count = json_res['count']
        for i in range(int(count)):
            tmp_list = []
            duration = int(int(json_res['route']['transits'][i]['cost']['duration']) / 60)
            fee = (json_res['route']['transits'][i]['cost']['transit_fee']).rstrip('.0')
            if fee == '':
                fee = 0
            else:
                fee = int(fee)
            if duration <= limit_time and fee <= limit_fee:
                tmp_list.append(duration)
                tmp_list.append(fee)
                res_list.append(tmp_list)

    if len(res_list) == 0:
        return None
    else:
        return res_list


# 将查询结果写入excel表
def out_excel(ll):
    wb = xw.Workbook()  # 创建工作簿
    sheet1 = wb.add_sheet("sheet1")  # 创建子表
    title = ['起始点', '总时间', 'TO 公司1', 'TO 公司2', '时间差', '费用1', '费用2']  # 设置表头
    for index in range(len(title)):
        sheet1.write(0, index, title[index])

    row = 1  # 从第二行开始写入数据
    for element in ll:
        sheet1.write(row, 0, element[0])
        for index in range(len(element[1])):
            sheet1.write(row, index + 1, element[1][index])
        row += 1
    wb.save('result.xls')


if __name__ == '__main__':
    # 爬虫获取北京市全部地铁站名，保存在列表中
    '''
    sub_name = get_subway()
    with open('stations.txt', 'w') as fp:
        for subway in sub_name:
            fp.write(subway + '\n')
    '''
    
    '''
    # 从文件中读取地铁站名
    sub_name = get_subway_fromfile('stations.txt')
    # 使用高德API将地铁站转化为经纬度坐标，并记录到文件中
    coordinate = dict()
    with open('coordinate.txt', 'w') as fp:
        for name in sub_name:
            value = get_location('北京市' + name)
            if value == None:
                print('[-] ' + name + ' get location error!')
            else:
                coordinate[name] = value
                fp.write(name + ': ' + value + '\n')
    '''
    
    # 为了防止API调用次数超过配额，将坐标保存到文件中，之后的操作可直接读取文件(站名：坐标)
    coor_dict = get_coor_fromfile('coordinate.txt')
    target1 = 'x, x'  # 公司1的经纬度
    target2 = 'y, y'  # 公司2的经纬度
    # 使用高德API计算地铁站之间的通勤时间（路径规划）
    # 将查询到的可选方案直接记录到文件中
    ress = dict()
    for key, value in coor_dict.items():
        # 获取每个地铁站到达目标地点的方案列表
        list1 = path_plan(value, target1, 0)
        list2 = path_plan(value, target2, 0)
        if list1 is not None and list2 is not None:
            # 以下处理每种方案的时间
            time1 = limit_time
            time2 = limit_time
            for i in range(len(list1)):
                if list1[i][0] <= time1:
                    time1 = list1[i][0]
                    fee1 = list1[i][1]
            for i in range(len(list2)):
                if list2[i][0] <= time2:
                    time2 = list2[i][0]
                    fee2 = list2[i][1]
            ress[key] = [time1 + time2, time1, time2, abs(time1 - time2), fee1, fee2]
    sort_ress = sorted(ress.items(), key=lambda d: d[1], reverse=False)
    out_excel(sort_ress)
    print('[+] Done!')
