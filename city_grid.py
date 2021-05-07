# 返回城市区域划分出的网格的坐标数组
import numpy as np


def generate_grids(start_long, start_lat, end_long, end_lat, resolution):
    """
    根据起始的经纬度和分辨率，生成需要需要的网格.
    方向为左上，右下，所以resolution应为 负数，否则未空
    :param start_long:
    :param start_lat:
    :param end_long:
    :param end_lat:
    :param resolution:
    :return:
    """
    assert start_long < end_long, '需要从左上到右下设置经度，start的经度应小于end的经度'
    assert start_lat > end_lat, '需要从左上到右下设置纬度，start的纬度应大于end的纬度'
    assert resolution > 0, 'resolution应大于0'


    grids_lib = []
    longs = np.arange(start_long, end_long, resolution)
    if longs[-1] != end_long:  # 切分余下的部分添加到网格里
        longs = np.append(longs, end_long)

    lats = np.arange(start_lat, end_lat, -resolution)
    if lats[-1] != end_lat:  # 切分余下的部分添加到网格里
        lats = np.append(lats, end_lat)
    for i in range(len(longs)-1):
        for j in range(len(lats)-1):
            grids_lib.append([round(float(longs[i]), 6), round(float(lats[j]), 6), round(float(longs[i+1]), 6), round(float(lats[j+1]), 6)])
            #yield [round(float(longs[i]),6),round(float(lats[j]),6),round(float(longs[i+1]),6),round(float(lats[j+1]),6)]
    return grids_lib  # 返回网格的四个坐标



#grids_lib = generate_grids(112.958507, 23.932988, 114.059957, 22.51436,0.1)
#print(grids_lib)