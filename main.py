from agent import ReActAgent
from tools import create_default_tools

def main():
    #创建工具
    tools = create_default_tools()
    
     #创建Agent
    agent = ReActAgent(tools, model="deepseek-chat")
    
    #测试用例
    test_cases = [
        "广州今天的天气怎么样",
        "帮我计算（325 + 125） *123 的结果",
        "今天是几号？广州的天气怎么样"
    ]
    
    for query in test_cases:
        result = agent.run(query)
        print(f"\n 回答为：{result}\n")
        print("-" *50)
        
if __name__ == "__main__":
    main()