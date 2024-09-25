import os
from typing import Dict, Optional, Union
import json
import requests

from qwen_agent.tools.base import BaseTool, register_tool
from difflib import get_close_matches

# 高德开放平台API
gaode_token = '***************'


@register_tool('amap_weather')
class AmapWeather(BaseTool):
    description = '获取对应城市的天气数据'
    parameters = [{
        'name': 'location',
        'type': 'string',
        'description': '城市/区具体名称，如果没有得到城市名则询问用户需要查询哪个城市的天气数据',
        'required': True
    }]

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)

        # remote call
        self.url = 'https://restapi.amap.com/v3/weather/weatherInfo?city={city}&key=********************'  # 此处更换为你的高德平台API

        import pandas as pd
        self.city_df = pd.read_excel(
            'https://modelscope.oss-cn-beijing.aliyuncs.com/resource/agent/AMap_adcode_citycode.xlsx')

        self.token = self.cfg.get('token', os.environ.get('AMAP_TOKEN', gaode_token))
        assert self.token != '', 'weather api token must be acquired through ' \
                                 'https://lbs.amap.com/api/webservice/guide/create-project/get-key and set by AMAP_TOKEN'

    def get_city_adcode(self, city_name):
        filtered_df = self.city_df[self.city_df['中文名'] == city_name]
        if len(filtered_df['adcode'].values) == 0:
            raise ValueError(f'location {city_name} not found, availables are {self.city_df["中文名"]}')
        else:
            return filtered_df['adcode'].values[0]

    def get_closest_city_name(self, city_name):
        city_names = self.city_df['中文名'].tolist()
        closest_match = get_close_matches(city_name, city_names, n=1, cutoff=0.6)
        if closest_match:
            return closest_match[0]
        else:
            return '没有找到对应的城市，请重新输入您需要查询天气的城市'

    def call(self, params: Union[str, dict], **kwargs) -> str:
        params = self._verify_json_format_args(params)
        location = params['location']
        location = self.get_closest_city_name(location)
        response = requests.get(self.url.format(city=self.get_city_adcode(location), key=self.token))
        data = response.json()
        if data['status'] == '0':
            raise RuntimeError(data)
        else:
            weather = data['lives'][0]['weather']
            temperature = data['lives'][0]['temperature']
            return f'{location}的天气是{weather}温度是{temperature}度。'
