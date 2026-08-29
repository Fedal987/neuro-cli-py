<div align="center">
    <h1 align="center">NeuroCode</h1>
    <h3>An Open-source AI Agent Application With High Performance based on Python</h3>
    <p>
        <img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python Version">
        <img src="https://img.shields.io/github/license/Fedal987/neuro-cli-py?label=License" alt="License">
        <img src="https://img.shields.io/badge/Status-In%20Development-yellow" alt="Status">
        <img src="https://img.shields.io/github/contributors/Fedal987/neuro-cli-py.svg?style=flat&label=Contributors" alt="Contributors">
        <img src="https://img.shields.io/github/forks/Fedal987/neuro-cli-py.svg?style=flat&label=Forks" alt="Forks">
        <img src="https://img.shields.io/github/stars/Fedal987/neuro-cli-py?style=flat&label=Stars" alt="Stars">
    </p>
    <img width="1080" height="211" alt="wide_evil" src="https://github.com/user-attachments/assets/64c40093-de30-4e22-94bb-041de0b6301d" />
    <hr>
</div>

## 介绍

NeuroCode 是一个基于大语言模型的可以与系统交互的Agent应用。

NeuroCode 不仅仅是一个聊天机器人，它还是一个非常有用的工具，其最终目的是实现类似于OpenClaw的系统交互应用

## TODO list:

- 更好的UI
- 单独写个窗口作为终端
- 写插件系统
- 写导入skills
- 用rust重写(?)

# 部署步骤  

## 环境需求  

- Git
- Python > 3.10

### Windows

```bash
git clone https://github.com/Fedal987/neurocode-py.git # 克隆仓库
pip install uv # 安装环境包管理器
uv venv # 创建虚拟环境
.venv\Scripts\activate # 激活虚拟环境
uv pip install requirements.txt # 安装依赖
```

### Linux(Arch fish shell)

```bash
git clone https://github.com/Fedal987/neurocode-py.git # 克隆仓库
python3 pip install uv # 安装环境包管理器
uv venv # 创建虚拟环境
source .venv\bin\activate.fish # 激活虚拟环境
uv pip install requirements.txt # 安装依赖
```

## 启动

```bash
uv run neuro.py
```

## 推理 Agent

项目默认使用 `src/main/prompt/reasoning_prompt.py` 中的推理提示词。推理和非推理提示词均通过 `src/main/tool/toolcall_utils.py` 创建共享的工具调用 Agent；它可以在当前工作目录内查看目录、读取和搜索文件，并通过工具调用完成修改与验证。关闭 `REASONING.ENABLED` 只会切换到非推理提示词并关闭思考参数，不会禁用工具调用。

相关选项位于 `config.toml` 的 `[REASONING]` 配置段，完整示例见 `templates/config.toml.bak`。默认情况下，写入文件或运行命令前会请求用户确认。权限提示中输入 `fc`（full control）会允许当前操作，并在本次运行的后续操作中不再询问；该选择不会写入配置。只有在可信环境中才应启用持久生效的 `AUTO_APPROVE`。
