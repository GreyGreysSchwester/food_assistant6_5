# main.py - Web Application (更新版)
import os
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from agents.food_agent import FoodAssistantAgent, analyze_nutrition
from config.settings import Settings

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_for_dev')

@app.route('/')
def index():
    """主页路由"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天API接口"""
    user_input = request.json.get('message', '')
    
    # 获取或创建智能体实例
    if 'agent_state' not in session:
        agent = FoodAssistantAgent()
        session['agent_state'] = {
            'state': agent.state.value,
            'user_profile': agent.user_profile.__dict__,
            'current_recipe': agent.current_recipe,
            'current_step_index': agent.current_step_index,
            'conversation_history': agent.conversation_history
        }
    else:
        # 从session重建智能体
        agent = FoodAssistantAgent()  # 重新创建实例
        from agents.food_agent import AgentState
        agent.state = AgentState(session['agent_state']['state'])
        agent.user_profile.__dict__ = session['agent_state']['user_profile']
        agent.current_recipe = session['agent_state']['current_recipe']
        agent.current_step_index = session['agent_state']['current_step_index']
        agent.conversation_history = session['agent_state']['conversation_history']
    
    try:
        # 处理用户输入
        response = agent.process_user_input(user_input)
        
        # 更新session中的状态
        session['agent_state'] = {
            'state': agent.state.value,
            'user_profile': agent.user_profile.__dict__,
            'current_recipe': agent.current_recipe,
            'current_step_index': agent.current_step_index,
            'conversation_history': agent.conversation_history
        }
        return jsonify({'response': response, 'status': 'success'})
    except Exception as e:
        return jsonify({'response': f'🐱 喵喵遇到了一点小问题：{str(e)}', 'status': 'error'})

@app.route('/api/nutrition', methods=['POST'])
def nutrition():
    """生成营养分析"""

    if 'agent_state' not in session:
        return jsonify({
            'status': 'error',
            'nutrition': '请先生成食谱'
        })

    current_recipe = session['agent_state'].get(
        'current_recipe'
    )

    if not current_recipe:
        return jsonify({
            'status': 'error',
            'nutrition': '请先生成食谱'
        })

    try:

        recipe_name = current_recipe['name']
        print('==recipe_name==')
        print(recipe_name)

        result = analyze_nutrition.invoke(
            {"recipe_name": recipe_name}
        )
        print('==nutrition_result==')
        print(result)
        print(type(result))

        return jsonify({
            'status': 'success',
            'nutrition': result
        })

    except Exception as e:

        return jsonify({
            'status': 'error',
            'nutrition': f'营养分析失败：{str(e)}'
        })

@app.route('/api/reset', methods=['POST'])
def reset_conversation():
    """重置对话"""
    # 清空session
    session.pop('agent_state', None)
    
    agent = FoodAssistantAgent()
    welcome_message = agent.reset_conversation()
    
    session['agent_state'] = {
        'state': agent.state.value,
        'user_profile': agent.user_profile.__dict__,
        'current_recipe': agent.current_recipe,
        'current_step_index': agent.current_step_index,
        'conversation_history': agent.conversation_history
    }
    
    return jsonify({'response': welcome_message})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)