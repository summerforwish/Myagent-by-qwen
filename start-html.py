import json
import os

import logging
from flask import Flask, request, Response, send_from_directory
from qwen_agent.agents import Assistant


app = Flask(__name__)

log_dir = './logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file = os.path.join(log_dir, 'app.log')
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    handlers=[
                        logging.FileHandler(log_file),
                        logging.StreamHandler()
                    ])

llm_cfg = {
    # 'model': '/model/Qwen1.5-14B-Chat',   #  使用vllm或者ollama启动的模型
    # 'model_server': 'http://0.0.0.0:8000',
    # 'api_key': 'EMPTY',
    'model': 'qwen-max',
    'model_server': 'dashscope',
    'api_key': '****************',  # 填写你的阿里云模型平台API
    'generate_cfg': {
        'top_p': 0.5
    }
}

system = '''你是"八重大人"，由猫猫开发的人工智能助手。
你能分析用户的需求并准确的找到合适的工具来解决用户的问题。
当用户的需求不涉及使用工具时，你需要尽可能合理而且友好的回答用户。
'''

tools = ['image_gen', 'amap_weather', 'news', 'inter_search']
files = ['./examples/resource/doc.pdf']
bot = Assistant(llm=llm_cfg,
                system_message=system,
                function_list=tools,
                files=files)


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


@app.route('/')
def index():
    return send_from_directory('.', 'summer.html')


@app.route('/agent/text', methods=['POST'])
def handle_query():
    try:
        data = request.json
        if not isinstance(data, list):
            output = json.dumps({'error': '请求内容必须为消息列表'})
            headers = {'type': 'error'}
            return Response(output, status=400, headers=headers, mimetype='application/json')

        logging.info(f'用户请求: {data}')
        messages = []
        for message in data:
            role = message.get('role', '')
            content = message.get('content', '')
            if role and content:
                messages.append({'role': role, 'content': content})
            else:
                output = json.dumps({'error': '消息格式不正确'})
                headers = {'type': 'error'}
                return Response(output, status=400, headers=headers, mimetype='application/json')

        response = []
        for res in bot.run(messages=messages):
            logging.info(f'机器人回应: {res}')
            response.append(res)

        messages.extend(response)

        last_res = response[-1]

        for element in last_res:
            if len(last_res) == 1 and last_res[0].get('role') == 'assistant':
                output = json.dumps({'content': last_res[0].get('content')})
                headers = {'type': 'text'}
                return Response(output, status=200, headers=headers, mimetype='application/json')

            # elif element.get('role') == 'function' and 'image_url' in element.get('content', ''):
            #     image_data = element['content']
            #     img_data = json.loads(image_data)
            #     image_url = img_data['image_url']
            #     if image_url:
            #         return jsonify({'content': image_url})

            #  文生图返回
            elif element.get('role') == 'function' and element.get('name') == 'image_gen':
                image_name = element['content']
                save_path = './static'
                result_file_path = os.path.join(save_path, image_name)
                if os.path.exists(result_file_path):
                    with open(result_file_path, 'rb') as f:
                        result_image = f.read()
                        logging.info(f'len(result_image): {len(result_image)}')

                    headers = {'image_name': image_name, 'type': 'text_img'}
                    return Response(result_image, headers=headers, mimetype="application/octet-stream")

        else:
            output = json.dumps({'content': last_res[-1].get('content')})
            headers = {'type': 'text'}
            return Response(output, status=200, headers=headers, mimetype='application/json')

    except Exception as e:
        logging.error(f'Error: {e}')
        output = json.dumps({'error': str(e)})
        headers = {'type': 'error'}
        return Response(output, status=500, headers=headers, mimetype='application/json')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8088)
