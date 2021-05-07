# 用于将json格式的泰森多边形数据和站点数据融合为一个csv，并将多边形坐标转化成高德地图API请求的坐标格式
# 并爬每个泰森多边形内的POI信息

import collections
import json
import pandas as pd
from urllib.parse import quote
import os
import time
from requests.adapters import HTTPAdapter
import requests




## TODO 1 POI类型编码，类型名或者编码都行，具体参见《高德地图POI分类编码表.xlsx》
typs = ['餐饮服务', '商场', '超级市场', '综合市场', '生活服务', '体育休闲服务', '医疗保健服务', '住宿服务', '风景名胜', '商务住宅', '政府机构及社会团体', '学校', '高等院校', '地铁站', '银行', '公司企业']
## TODO 2. 高德开放平台密钥
# gaode_key = ['高德秘钥1', '高德秘钥2']
gaode_key = []
# TODO 3.输出数据坐标系,1为高德GCJ20坐标系，2WGS84坐标系，3百度BD09坐标系
coord = 2

poi_pology_search_url = 'https://restapi.amap.com/v3/place/polygon'
# 创建存储key的列表
buffer_keys = collections.deque(maxlen=len(gaode_key))

json_filename = 'taison_polygon.json'
csv_filename = '市区站点.csv'
out_put_name = '市区站点_坐标_货量_泰森多边形.csv'
# 用于存储所有poi类型在各个多边形内的数量的字典，用index作为索引
type_poi_sum = {}

def data_merge():
    taison_data = {'id_index': [], 'geometry': [], 'gaode_geometry': []}  # 用于将json数据构造成df数据
    with open(json_filename) as f:
        ts_polygon = json.load(f)
    for i, feature in enumerate(ts_polygon['features']):
        taison_data['id_index'].append(i)
        # 将geometry转化为GMNS格式
        geo_gmns_Str = 'POLYGON ' + str(feature['geometry']['coordinates'][0]).replace('[', '(').replace(']', ')').replace(' ', '').replace(',', ' ').replace(') (', ',')
        taison_data['geometry'].append(geo_gmns_Str)
        # 将geometry转化成高德地图API请求的坐标格式
        geo_arr = feature['geometry']['coordinates'][0]
        gaode_geometry_str = ''
        for coord in geo_arr:
            gaode_geometry_str += str(coord[0]) + ',' + str(coord[1]) + '|'
        gaode_geometry_str = gaode_geometry_str[0:-1]  # 截去最后一个 |
        taison_data['gaode_geometry'].append(gaode_geometry_str)
    df_taison_data = pd.DataFrame(taison_data)  # 构造的df格式的数据
    df_station = pd.read_csv(csv_filename, encoding="GBK")
    # 将泰森多边形坐标和站点信息文件融合为一个csv文件
    merge_data = pd.merge(df_station, df_taison_data, left_on=['id_num'], right_on=['id_index'], how='inner')
    merge_data.to_csv(out_put_name, index=False, encoding="GBK")
    # 返回df形式的所有信息
    return merge_data

# 以上是数据处理工作
#######################################################################################################################
# 以下为爬每个泰森多边形内的POI信息

def init_queen():
    for i in range(len(gaode_key)):
        buffer_keys.append(gaode_key[i])
    print('当前可供使用的高德密钥：', buffer_keys)


def getpois(geo_str, keywords):
    if buffer_keys.maxlen == 0:
        print('密钥已经用尽，程序退出！！！！！！！！！！！！！！！')
        exit(0)
    amap_key = buffer_keys[0]  # 总是获取队列中的第一个密钥,amap_key是当前使用的key

    i = 1
    poilist = []
    while True:  # 使用while循环不断分页获取数据
        result = getpoi_page(geo_str, keywords, i, amap_key)
        print("当前爬取结果:", result)
        if result != None:
            result = json.loads(result)  # 将字符串转换为json
            try:
                if result['count'] == '0':
                    break
            except Exception as e:
                print('出现异常：', e)

            if result['infocode'] == '10001' or result['infocode'] == '10003':
                print(result)
                print('无效的密钥！！！！！！！！！！！！！，重新切换密钥进行爬取')
                buffer_keys.remove(buffer_keys[0])
                try:
                    amap_key = buffer_keys[0]  # 总是获取队列中的第一个密钥
                except Exception as e:
                    print('密钥已经用尽，程序退出...')
                    exit(0)
                result = getpoi_page(geo_str, keywords, i, amap_key)
                result = json.loads(result)
            hand(poilist, result)
        i = i + 1
    return poilist


# 将返回的poi数据装入集合返回
def hand(poilist, result):
    # result = json.loads(result)  # 将字符串转换为json
    pois = result['pois']
    for i in range(len(pois)):
        poilist.append(pois[i])


# 单页获取pois
def getpoi_page(geo_str, types, page, key):
    polygon = geo_str
    req_url = poi_pology_search_url + "?key=" + key + '&extensions=all&types=' + quote(
        types) + '&polygon=' + polygon + '&offset=25' + '&page=' + str(
        page) + '&output=json'
    print('请求url：', req_url)

    s = requests.Session()
    s.mount('http://', HTTPAdapter(max_retries=5))
    s.mount('https://', HTTPAdapter(max_retries=5))
    try:
        data = s.get(req_url, timeout=5)
        return data.text
    except requests.exceptions.RequestException as e:
        data = s.get(req_url, timeout=5)
        return data.text
    return None


# 按每一个POI类型调用这个函数
def get_data_type(df_merge_data, keyword, coord):
    geo_list = df_merge_data['gaode_geometry'].tolist()
    begin_time = time.time()

    print('==========================正式开始爬取================================')
    # 存储这个类型的POI各个多边形内数量的数组
    poi_num = []
    # 数组索引，用于后续的merge
    index_geo = []
    for i, geo_str in enumerate(geo_list):
        one_pology_data = getpois(geo_str, keyword)
        poi_num.append(len(one_pology_data))
        index_geo.append(i)
        print('===================================当前矩形范围：', geo_str)
    # 将存储这个类型的POI各个网格内数量的数组push到全局变量里存储所有类型poi数量汇总的数组
    type_poi_sum[keyword] = poi_num
    type_poi_sum['index'] = index_geo

    end_time = time.time()
    print('耗时：', str(end_time - begin_time))







if __name__ == '__main__':
    # 数据融合处理
    origin_data = data_merge()
    # 将高德key push到列表
    init_queen()
    # 开始爬虫
    for type in typs:
        get_data_type(origin_data, type, coord)
    # 融合成最终数据
    df_type_poi_sum = pd.DataFrame(type_poi_sum)
    final_merge_data = pd.merge(origin_data, df_type_poi_sum, left_on=['id_index'], right_on=['index'], how='inner')
    final_merge_data.to_csv("汇总数据.csv", index=False, encoding="GBK")







