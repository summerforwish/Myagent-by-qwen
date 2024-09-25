import urllib.parse
import json5
from qwen_agent.tools.base import BaseTool, register_tool
import os
import requests
import base64
import hashlib
import hmac
import json
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from PIL import Image
from io import BytesIO


class AssembleHeaderException(Exception):
    def __init__(self, msg):
        self.message = msg


class Url:
    def __init__(this, host, path, schema):
        this.host = host
        this.path = path
        this.schema = schema


# calculate sha256 and encode to base64
def sha256base64(data):
    sha256 = hashlib.sha256()
    sha256.update(data)
    digest = base64.b64encode(sha256.digest()).decode(encoding="utf-8")
    return digest


def parse_url(requset_url):
    stidx = requset_url.index("://")
    host = requset_url[stidx + 3:]
    schema = requset_url[: stidx + 3]
    edidx = host.index("/")
    if edidx <= 0:
        raise AssembleHeaderException("invalid request url:" + requset_url)
    path = host[edidx:]
    host = host[:edidx]
    u = Url(host, path, schema)
    return u


def assemble_ws_auth_url(requset_url, method="GET", api_key="", api_secret=""):
    u = parse_url(requset_url)
    host = u.host
    path = u.path
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    signature_origin = "host: {}\ndate: {}\n{} {} HTTP/1.1".format(
        host, date, method, path
    )
    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature_sha = base64.b64encode(signature_sha).decode(encoding="utf-8")
    authorization_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
        encoding="utf-8"
    )
    values = {"host": host, "date": date, "authorization": authorization}
    return requset_url + "?" + urlencode(values)


def get_body(appid, text):
    body = {
        "header": {"app_id": appid, "uid": "123456789"},
        "parameter": {
            "chat": {"domain": "general", "temperature": 0.5, "max_tokens": 4096}
        },
        "payload": {"message": {"text": [{"role": "user", "content": text}]}},
    }
    return body


def spark_response(text, appid, apikey, apisecret):
    host = "http://spark-api.cn-huabei-1.xf-yun.com/v2.1/tti"
    url = assemble_ws_auth_url(
        host, method="POST", api_key=apikey, api_secret=apisecret
    )
    content = get_body(appid, text)
    response = requests.post(
        url, json=content, headers={"content-type": "application/json"}
    ).text
    return response


def img_generation(prompt):
    response = spark_response(
        text=prompt,
        appid="******",  # 星火应用平台API
        apikey="******************",  # 星火应用平台API
        apisecret="******************",  # 星火应用平台API
    )
    data = json.loads(response)
    code = data["header"]["code"]
    if code != 0:
        return []
    else:
        text = data["payload"]["choices"]["text"]
        image_content = text[0]
        image_base = image_content["content"]

    image_data = base64.b64decode(image_base)
    image = Image.open(BytesIO(image_data))

    # 生成文件名
    now = datetime.now().strftime('%Y%m%d%H%M%S')

    file_name = f"{now}_paint.png"
    save_path = './static'
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    file_path = os.path.join(save_path, file_name)

    image.save(file_path)

    return file_name


@register_tool('image_gen')
class ImageGen(BaseTool):
    description = 'AI绘画（图像生成）服务，输入绘画需求和文本描述，返回根据文本信息绘制的图片名字。'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': '详细描述了希望生成的图像具有什么内容，例如人物、环境、动作等细节描述',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        # `params` 是由 LLM 智能体生成的参数。
        prompt = json5.loads(params)['prompt']
        # prompt = urllib.parse.quote(prompt)
        print('prompt>>>>>>', prompt)
        file_name = img_generation(prompt)
        print('file_name>>>>>>>', file_name)
        return file_name
