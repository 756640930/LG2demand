from urllib.parse import quote
import json
import os
from transCoordinateSystem import gcj02_to_wgs84, gcj02_to_bd09
import area_boundary as area_boundary
import city_grid as city_grid
import time
import collections
import pandas as pd
from requests.adapters import HTTPAdapter
import requests
from math import ceil
#from shp import trans_point_to_shp




#################################################需要修改###########################################################

## TODO 1.划分的网格距离，0.02-0.05最佳
pology_split_distance = 0.05  # 此数值单位不是km，是经纬度坐标的间隔

## TODO 2. 城市编码，参见高德城市编码表
city_code = '110108'

## TODO 3. 高德开放平台密钥
# gaode_key = ['高德秘钥1', '高德秘钥2']
gaode_key = []

# TODO 4.输出数据坐标系,1为高德GCJ20坐标系，2WGS84坐标系，3百度BD09坐标系
coord = 2

############################################以下不需要动#######################################################################


# POI类型编码，类型名或者编码都行，具体参见《高德地图POI分类编码表.xlsx》
typs = ['餐饮服务', '商场', '超级市场', '综合市场', '生活服务', '体育休闲服务', '医疗保健服务', '住宿服务', '风景名胜', '商务住宅', '政府机构及社会团体', '学校', '高等院校', '地铁站', '银行', '公司企业']
poi_pology_search_url = 'https://restapi.amap.com/v3/place/polygon'
# 创建存储key的列表
buffer_keys = collections.deque(maxlen=len(gaode_key))
# 创建存储统计每个网格内各类poi总和数
poi_sum_num = {
    '餐饮服务': None,
    '商场': None,
    '超级市场': None,
    '综合市场': None,
    '生活服务': None,
    '体育休闲服务': None,
    '医疗保健服务': None,
    '住宿服务': None,
    '风景名胜': None,
    '商务住宅': None,
    '政府机构及社会团体': None,
    '学校': None,
    '高等院校': None,
    '地铁站': None,
    '银行': None,
    '公司企业': None
}
# 线性回归的系数
coefficient = {
    '餐饮服务': -0.168,
    '商场': -5.008,
    '超级市场': -0.515,
    '综合市场': 0.201,
    '生活服务': 0.152,
    '体育休闲服务': 0.910,
    '医疗保健服务': -0.474,
    '住宿服务': 1.303,
    '风景名胜': -0.043,
    '商务住宅': -1.995,
    '政府机构及社会团体': -0.060,
    '学校': -0.705,
    '高等院校': 0.489,
    '地铁站': 55.1,
    '银行': 2.87,
    '公司企业': 0.046
}
# 线性回归的常数
constValue = 469
# 存储每个grid的边界点坐标的数组
grid_geo_arr = []
# 存储每个grid的id数组
grid_id = []


def init_queen():
    for i in range(len(gaode_key)):
        buffer_keys.append(gaode_key[i])
    print('当前可供使用的高德密钥：', buffer_keys)


# 根据城市名称和分类关键字获取poi数据
def getpois(grids, keywords):
    if buffer_keys.maxlen == 0:
        print('密钥已经用尽，程序退出！！！！！！！！！！！！！！！')
        exit(0)
    amap_key = buffer_keys[0]  # 总是获取队列中的第一个密钥,amap_key是当前使用的key

    i = 1
    poilist = []
    while True:  # 使用while循环不断分页获取数据
        result = getpoi_page(grids, keywords, i, amap_key)
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
                result = getpoi_page(grids, keywords, i, amap_key)
                result = json.loads(result)
            hand(poilist, result)
        i = i + 1
    return poilist


# 数据写入csv文件中
def write_to_csv(poilist, citycode, classfield, coord):
    data_csv = {}
    lons, lats, names, addresss, pnames, citynames, business_areas, types, typecodes, ids, type_1s, type_2s, type_3s, type_4s = [], [], [], [], [], [], [], [], [], [], [], [], [], []

    if len(poilist) == 0:
        print("处理完成，当前citycode:" + str(citycode), ", classfield为：", str(classfield) + "，数据为空，，，结束.......")
        return None, None

    for i in range(len(poilist)):
        location = poilist[i].get('location')
        name = poilist[i].get('name')
        address = poilist[i].get('address')
        pname = poilist[i].get('pname')
        cityname = poilist[i].get('cityname')
        business_area = poilist[i].get('business_area')
        type = poilist[i].get('type')
        typecode = poilist[i].get('typecode')
        lng = str(location).split(",")[0]
        lat = str(location).split(",")[1]
        id = poilist[i].get('id')

        if (coord == 2):
            result = gcj02_to_wgs84(float(lng), float(lat))
            lng = result[0]
            lat = result[1]
        if (coord == 3):
            result = gcj02_to_bd09(float(lng), float(lat))
            lng = result[0]
            lat = result[1]
        type_1, type_2, type_3, type_4 = '','','',''
        if str(type) != None and str(type) != '':
            type_strs = type.split(';')
            for i in range(len(type_strs)):
                ty = type_strs[i]
                if i == 0:
                    type_1 = ty
                elif i == 1:
                    type_2 = ty
                elif i == 2:
                    type_3 = ty
                elif i == 3:
                    type_4 = ty

        lons.append(lng)
        lats.append(lat)
        names.append(name)
        addresss.append(address)
        pnames.append(pname)
        citynames.append(cityname)
        if business_area == []:
            business_area = ''
        business_areas.append(business_area)
        types.append(type)
        typecodes.append(typecode)
        ids.append(id)
        type_1s.append(type_1)
        type_2s.append(type_2)
        type_3s.append(type_3)
        type_4s.append(type_4)
    data_csv['lon'], data_csv['lat'], data_csv['name'], data_csv['address'], data_csv['pname'], \
    data_csv['cityname'], data_csv['business_area'], data_csv['type'], data_csv['typecode'], data_csv['id'], data_csv[
        'type1'], data_csv['type2'], data_csv['type3'], data_csv['type4'] = \
        lons, lats, names, addresss, pnames, citynames, business_areas, types, typecodes, ids, type_1s, type_2s, type_3s, type_4s

    df = pd.DataFrame(data_csv)

    folder_name = 'poi-' + citycode + "-" + classfield
    folder_name_full = 'data' + os.sep + folder_name + os.sep
    if os.path.exists(folder_name_full) is False:
        os.makedirs(folder_name_full)
    file_name = 'poi-' + citycode + "-" + classfield + ".csv"
    file_path = folder_name_full + file_name
    df.to_csv(file_path, index=False, encoding='utf_8_sig')
    print('写入成功')
    return folder_name_full, file_name


# 将返回的poi数据装入集合返回
def hand(poilist, result):
    # result = json.loads(result)  # 将字符串转换为json
    pois = result['pois']
    for i in range(len(pois)):
        poilist.append(pois[i])


# 单页获取pois
def getpoi_page(grids, types, page, key):
    polygon = str(grids[0]) + "," + str(grids[1]) + "|" + str(grids[2]) + "," + str(grids[3])
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


def get_drids(min_lng, max_lat, max_lng, min_lat, keyword, key, pology_split_distance, all_grids):
    grids_lib = city_grid.generate_grids(min_lng, max_lat, max_lng, min_lat, pology_split_distance)

    print('划分后的网格数：', len(grids_lib))
    print(grids_lib)

    # 3. 根据生成的网格爬取数据，验证网格大小是否合适，如果不合适的话，需要继续切分网格
    for grid in grids_lib:
        one_pology_data = getpoi_page(grid, keyword, 1, key)
        data = json.loads(one_pology_data)
        print(data)

        while int(data['count']) > 890:
            get_drids(grid[0], grid[1], grid[2], grid[3], keyword, key, pology_split_distance / 2, all_grids)


        all_grids.append(grid)
    return all_grids


def get_data(city, keyword, coord):
    # 1. 获取城市边界的最大、最小经纬度
    amap_key = buffer_keys[0]  # 总是获取队列中的第一个密钥
    max_lng, min_lng, max_lat, min_lat = area_boundary.getlnglat(city, amap_key) # 返回城市区域最大最小经纬度坐标

    print('当前城市：', city, "max_lng, min_lng, max_lat, min_lat：", max_lng, min_lng, max_lat, min_lat)

    # 2. 生成网格切片格式：

    grids_lib = city_grid.generate_grids(min_lng, max_lat, max_lng, min_lat, pology_split_distance)
    # 全局变量存储网格坐标
    if not grid_geo_arr:
        grid_geo_arr.extend(grids_lib)
    # 网格id按顺序0，1，2，3。。。存入到grid_id数组
    if not grid_id:
        for i in range(len(grids_lib)):
            grid_id.append(i)

    print('划分后的网格数：', len(grids_lib))
    print(grids_lib)

    all_data = []
    begin_time = time.time()

    print('==========================正式开始爬取================================')
    # 存储这个类型的POI各个网格内数量的数组
    poi_num = []
    for grid in grids_lib:
        # grid格式：[112.23, 23.23, 112.24, 23.22]
        one_pology_data = getpois(grid, keyword)
        poi_num.append(len(one_pology_data))

        print('===================================当前矩形范围：', grid)

        all_data.extend(one_pology_data)
    # 将存储这个类型的POI各个网格内数量的数组push到全局变量里存储所有类型poi数量汇总的数组
    poi_sum_num[keyword] = poi_num

    end_time = time.time()
    print('全部：', str(len(grids_lib)) + '个矩形范围', '  耗时：', str(end_time - begin_time),
          '正在写入CSV文件中')
    file_folder, file_name = write_to_csv(all_data, city, keyword, coord)
    # 写入shp
    #if file_folder is not None:
        #trans_point_to_shp(file_folder, file_name, 0, 1, pology_split_distance, keyword)
def Lgdemand_output(city_code, grid_id, split_distance, grid_geo_arr, poi_sum_num, typs):
    output_csv = {}
    city_code_list = []
    grid_distance_list = []
    for i in range(len(grid_id)):
        city_code_list.append(city_code)
        grid_distance_list.append(split_distance)
    output_csv['city_code'] = city_code_list
    output_csv['grid_distance'] = grid_distance_list


    # 对grid坐标进行整理成4个点坐标geometry格式
    grids_geometry = list()
    pre_goods = list()
    for i in range(len(grid_geo_arr)):
        geometry_string = 'POLYGON (('
        geometry_string = geometry_string + str(grid_geo_arr[i][0]) + ' '
        geometry_string = geometry_string + str(grid_geo_arr[i][1]) + ','
        geometry_string = geometry_string + str(grid_geo_arr[i][2]) + ' '
        geometry_string = geometry_string + str(grid_geo_arr[i][1]) + ','
        geometry_string = geometry_string + str(grid_geo_arr[i][2]) + ' '
        geometry_string = geometry_string + str(grid_geo_arr[i][3]) + ','
        geometry_string = geometry_string + str(grid_geo_arr[i][0]) + ' '
        geometry_string = geometry_string + str(grid_geo_arr[i][3]) + ','
        geometry_string = geometry_string + str(grid_geo_arr[i][0]) + ' '
        geometry_string = geometry_string + str(grid_geo_arr[i][1]) + '))'


        grids_geometry.append(geometry_string)

        # 预测货量计算
        pre = 0
        for key in poi_sum_num:
            pre = pre + poi_sum_num[key][i]*coefficient[key]
        pre += constValue
        # 如果预测货量为负数，则赋值1
        if pre <= 0:
            pre = 1
        pre = ceil(pre / 0.163)
        pre_goods.append(pre)



    output_csv['grid_id'], output_csv['geometry'] = grid_id, grids_geometry
    for val in typs:
        output_csv[val] = poi_sum_num[val]
    output_csv['goods_predection'] = pre_goods
    df = pd.DataFrame(output_csv)
    df.to_csv('LG2demand.csv', index=False, encoding='utf_8_sig')







if __name__ == '__main__':
    # 初始化密钥队列
    init_queen()

    for type in typs:
        get_data(city_code, type, coord)
    # 输出lgdemand文件
    Lgdemand_output(city_code, grid_id, pology_split_distance, grid_geo_arr, poi_sum_num, typs)
