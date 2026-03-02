# 🥇 黄金斐波那契分析系统 - 部署指南

## 已创建的资源

### GitHub 仓库
- **URL**: https://github.com/bylaikaby/gold-fibonacci-streamlit
- **状态**: ✅ 已推送代码

### 文件结构
```
├── streamlit_app.py      # 主应用文件
├── requirements.txt      # Python依赖
├── .streamlit/
│   └── config.toml      # Streamlit配置
└── DEPLOY.md            # 本文件
```

---

## 部署到 Streamlit Cloud (推荐)

### 方法一：通过网页界面 (最简单)

1. 访问 https://streamlit.io/cloud
2. 点击 "Sign in" 使用 GitHub 账号登录
3. 点击 "New app"
4. 选择:
   - **Repository**: `bylaikaby/gold-fibonacci-streamlit`
   - **Branch**: `master`
   - **Main file path**: `streamlit_app.py`
5. 点击 "Deploy"

### 方法二：通过 Streamlit Cloud CLI

```bash
# 安装 streamlit-cloud
pip install streamlit-cloud

# 登录
stcloud login

# 部署
stcloud deploy --app-file streamlit_app.py
```

---

## 部署到其他平台

### Railway (免费)
1. 访问 https://railway.app
2. 从 GitHub 导入项目
3. 自动检测 Python 应用
4. 部署

### Render (免费)
1. 访问 https://render.com
2. 创建 New Web Service
3. 连接 GitHub 仓库
4. 设置:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run streamlit_app.py --server.port $PORT`

### Hugging Face Spaces (免费)
1. 访问 https://huggingface.co/spaces
2. 创建 New Space
3. 选择 Streamlit SDK
4. 上传文件或连接 GitHub

---

## 本地运行

```bash
# 克隆仓库
git clone https://github.com/bylaikaby/gold-fibonacci-streamlit.git
cd gold-fibonacci-streamlit

# 安装依赖
pip install -r requirements.txt

# 运行应用
streamlit run streamlit_app.py
```

应用将在 http://localhost:8501 启动

---

## 应用功能

- 📈 **实时金价**: 从多个免费API获取黄金/白银/铂金/钯金价格
- 📊 **历史数据**: Yahoo Finance 历史K线数据
- 📐 **斐波那契分析**: 自动计算回调位和扩展位
- 🎯 **交易建议**: 基于技术分析生成买卖建议
- 📉 **技术指标**: RSI、MACD、均线、布林带

---

## 数据源

1. **Yahoo Finance (yfinance)** - 历史K线 + 实时价格
2. **Metals.Live API** - 实时价格
3. **FreeGoldAPI.com** - 历史数据
4. **Frankfurter API** - 汇率转换

---

## 技术栈

- Python 3.11+
- Streamlit 1.28+
- Plotly 5.18+
- yfinance 0.2+
- Pandas / NumPy
