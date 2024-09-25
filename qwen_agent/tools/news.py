import requests
import os
import urllib.parse
import json5
from qwen_agent.tools.base import BaseTool, register_tool

import requests
import os
import json

# 探数API
tanshu_api = "****************************"


def fetch_and_process_news(article_type):
    # 基本的API URL
    base_url = "http://api.tanshuapi.com/api/toutiao/v1/index"

    # 请求参数
    params = {
        "key": tanshu_api,
        "type": article_type,
        "num": 5,
        "start": 0
    }

    # 发送GET请求
    response = requests.get(base_url, params=params)

    # 检查请求是否成功
    if response.status_code == 200:
        response_data = response.json()

        # 检查API调用是否成功
        if response_data['code'] == 1:
            # 准备存储结果的列表
            result_list = []

            # 遍历新闻条目
            for article in response_data['data']['list']:
                # 提取必要信息
                title = article.get('title', '无标题')
                time = article.get('time', '时间未知')
                pic_url = article.get('pic', '')
                content = article.get('content', '内容未知')
                weburl = article.get('weburl', '')

                # 检查图片链接是否存在
                if pic_url:
                    # 从URL中提取图片名称
                    pic_name = pic_url.split('/')[-1]

                    # 定义保存图片的路径
                    directory_path = './news'
                    save_path = os.path.join(directory_path, pic_name)

                    # 发送HTTP请求获取图片
                    img_response = requests.get(pic_url, stream=True)

                    if img_response.status_code == 200:
                        # 确保保存图片的目录存在
                        if not os.path.exists(directory_path):
                            os.makedirs(directory_path)

                        # 打开文件准备写入
                        with open(save_path, 'wb') as f:
                            for chunk in img_response.iter_content(1024):
                                f.write(chunk)
                        print(f"图片已下载并保存为: {save_path}")

                        # 将图片保存路径添加到文章信息中
                        article['pic'] = pic_name
                    else:
                        return f"图片下载失败，状态码：{img_response.status_code}"

                # 将处理后的文章信息添加到结果列表
                result_list.append({
                    'title': title,
                    'time': time,
                    'pic': pic_name if pic_url else '无图片',
                    'weburl': weburl if weburl else '无链接',
                    'content': content[:200]
                })

            return result_list
        else:
            return f"API调用失败，错误信息：{response_data['msg']}"
    else:
        return f"请求失败，状态码：{response.status_code}"


# 使用示例
# article_type = '头条'  # 根据需要替换为其他类型
# articles = fetch_and_process_news(article_type)
# print(json.dumps(articles, ensure_ascii=False, indent=2))

@register_tool('news')
class QueryNews(BaseTool):
    description = '当用户输入提及新闻、资讯等问题时调用该接口，并根据用户提问从"头条","新闻","国内","国际","政治","财经","体育","娱乐","军事","教育","科技","NBA","股票","星座","女性","育儿"中选择一个作为prompt进行接口的调用'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': '判断需要进行新闻资讯搜索的类型名',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        # `params` 是由 LLM 智能体生成的参数。
        prompt = json5.loads(params)['prompt']
        # prompt = urllib.parse.quote(prompt)

        result = fetch_and_process_news(prompt)
        return result
