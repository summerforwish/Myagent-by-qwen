import re
import json
import httpx
from urllib.parse import quote
from bs4 import BeautifulSoup
import asyncio
import urllib.parse
import json5
from qwen_agent.tools.base import BaseTool, register_tool

# Tavily搜索
tavily_api_key = "**************************"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                  " Chrome/124.0.0.0 Safari/537.36"
}


def get_assemble_prompt(question: str, agent_data: str):
    """获取聚合提示"""
    prompt = f'''
    先学习 <AGENT_DATA></AGENT_DATA> 标记中的知识，然后回答我的问题。
    我的要求是：
        1. 不要提及你从标记中学习知识，只需要回答问题
        2. 如果提供的知识为空或者你无法学习我的知识，你不要说我提供的信息为空，直接根据你的理解回答我的问题即可
    下面是我提供的知识:
    <AGENT_DATA>
        {agent_data}
    </AGENT_DATA>
    我的问题是：
    """
    {question}
    """
    '''
    return prompt


def get_page_pure_text(html_text: str):
    # 提取文字
    pure_text = BeautifulSoup(html_text, "html.parser").get_text()
    pure_text = re.sub(r'\s+', '\n', pure_text).strip()
    return pure_text


def parse_baidu_search_result(html_text: str):
    # 解析百度搜索页内容
    soup = BeautifulSoup(html_text, "html.parser")
    soup_list = soup.select(".c-container:not([class*=' '])")

    res_list = []

    for item in soup_list:
        s_data = re.findall(r"<!--s-data:(.*?)-->", str(item))
        if not s_data:
            continue
        try:
            s_data = json.loads(s_data[0])
        except Exception as e:
            print(f"WARNING: 有信息获取失败，但不影响 {e}")
            continue
        item_dict = {
            "title": s_data["title"],
            "content": s_data["contentText"],
            "url": s_data["tplData"]["classicInfo"]["url"]
        }
        res_list.append(item_dict)
    return res_list


async def search_baidu(query: str, max_results: int = 5):
    """百度搜索"""
    url = f"https://www.baidu.com/s?wd={query}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers)
        if r.status_code > 399:
            return "内容获取失败"
        results = parse_baidu_search_result(r.content.decode("utf8"))[:max_results]
        raw_content = "\n".join([f"《{item['title']}》:{item['content']}" for item in results])
        print('baidu>>>>>', raw_content)
        return raw_content


async def search_bing(query: str):
    """必应搜索"""
    query = quote(query)
    url = f"https://cn.bing.com/search?q={query}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers)
        pure_text = get_page_pure_text(r.text)
        print('bing>>>>>>', pure_text)
        return pure_text


async def search_tavily(query: str, api_key: str = None, max_results=3):
    """泰维利亚搜索"""
    url = "https://api.tavily.com/search"

    data = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "include_images": False,
        "include_raw_content": False,
        "max_results": max_results,
        "include_domains": [],
        "exclude_domains": []
    }
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, headers=headers, json=data)
            results = r.json()["results"]

            # 压缩内容，只提取 title 和 content
            results = [f"《{item['title']}》:{item['content']}" for item in results]
            print('tavily>>>>>>', results)
            return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            print(f"WARNING: {query} 内容提取失败, {e}")
            return "内容提取失败"


async def get_url_content(url: str):
    """提取指定页面内容"""
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, headers=headers)
            pure_text = get_page_pure_text(r.text)
        except Exception as e:
            print(f"WARNING: {url} 内容提取失败, {e}")
            return "内容提取失败"
        return pure_text


class Interner_search:
    """联网查询"""

    @staticmethod
    async def get_search_result(llm_res):
        # 联网搜索
        if tavily_api_key:
            search_result = await search_tavily(query=llm_res, api_key=tavily_api_key)
        else:
            search_result = await search_baidu(query=llm_res)
        result = f"\"{llm_res}\" 在搜索引擎的搜索结果是：{search_result}"
        return result


async def intel2search(question):
    search_data = await Interner_search.get_search_result(question)
    assemble_prompt = get_assemble_prompt(question=question, agent_data=search_data)
    return assemble_prompt


@register_tool('inter_search')
class Inter2search(BaseTool):
    description = '当你不知道答案或者无法直接回答用户的问题时，对用户的提问进行联网搜索'
    parameters = [{
        'name': 'prompt',
        'type': 'string',
        'description': '需要联网搜索的相关内容',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        # `params` 是由 LLM 智能体生成的参数。
        prompt = json5.loads(params)['prompt']
        search_out = asyncio.run(intel2search(prompt))
        return search_out
