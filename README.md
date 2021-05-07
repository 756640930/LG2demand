# LG2demand
#一款城市区域快递需求量估计的爬虫工具
LG2demand是一款开源的城市网格区域快递量估计工具。根据用户自定义选择城市（区）和网格划分的大小，LG2demand可基于高德地图API自动爬取网格内各类兴趣点（point of interest，POI）信息，并基于网格内各类型POI的数量估计每个网格的一周的快递需求量。

使用说明：
用户根据使用目的自主修改程序app.py中以下四项：
（1）选择城市（区），城市编码参照高德城市编码表https://lbs.amap.com/api/webservice/download
（2）指定城市（区）划分网格的大小，推荐网格大小在0.02–0.05之间。
（3）申请高德开放密钥web服务key https://console.amap.com/dev/index
（4）选择输出坐标系：1为高德GCJ20坐标系，2为WGS84坐标系，3为百度BD09坐标系。
（5）运行app.py
>>> city_code = ‘110108’
>>> pology_split_distance = 0.05
>>> gaode_key = [‘高德密钥1’, ‘高德密钥2’, ‘高德密钥3’, ‘高德密钥4’]
>>> coord = 2

输出文件可上传到在线网页：（https://756640930.github.io/gmns_upload_file/index.html#/） 可视化
