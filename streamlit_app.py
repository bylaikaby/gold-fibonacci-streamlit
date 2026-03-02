"""
黄金斐波那契分析系统 v4.2 - Streamlit版
基于 fib_gui_best.py 转换
支持自动识别 A/B/C 三点

数据源:
1. Yahoo Finance (yfinance) - 历史K线 + 实时价格
2. Metals.Live API - 实时价格
3. FreeGoldAPI.com - 历史数据
4. Frankfurter API - 汇率转换
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# 设置页面配置（必须在其他st命令之前）
st.set_page_config(
    page_title="🥇 黄金斐波那契分析系统 v4.2",
    page_icon="🥇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 尝试导入yfinance
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    st.warning("⚠️ 请安装 yfinance: pip install yfinance")

# 尝试导入plotly
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    st.error("⚠️ 请安装 plotly: pip install plotly")

# ============================================
# 常量定义
# ============================================

class Metal(Enum):
    """贵金属类型"""
    GOLD = ("XAU", "GC=F", "黄金", "#FFD700")
    SILVER = ("XAG", "SI=F", "白银", "#C0C0C0")
    PLATINUM = ("XPT", "PL=F", "铂金", "#E5E4E2")
    PALLADIUM = ("XPD", "PA=F", "钯金", "#CED0DD")
    
    def __init__(self, api_symbol, yf_symbol, cn_name, color):
        self.api_symbol = api_symbol
        self.yf_symbol = yf_symbol
        self.cn_name = cn_name
        self.color = color


# ============================================
# 免费数据获取器 (无需API Key)
# ============================================

class FreeGoldFetcher:
    """
    完全免费的金价获取器
    无需任何API Key
    """
    
    def __init__(self):
        self.current_price = None
        self.last_update = None
        self.data_source = None
        self.price_cache = {}
    
    def fetch_from_yahoo(self, metal: Metal = Metal.GOLD, 
                         period: str = "1d") -> Optional[float]:
        """
        Yahoo Finance - 完全免费，无需注册
        支持实时价格和历史数据
        """
        if not HAS_YFINANCE:
            return None
        
        try:
            ticker = yf.Ticker(metal.yf_symbol)
            data = ticker.history(period=period)
            
            if not data.empty:
                self.current_price = float(data['Close'].iloc[-1])
                self.data_source = "Yahoo Finance"
                self.last_update = datetime.now()
                return self.current_price
                
        except Exception as e:
            st.error(f"Yahoo Finance错误: {e}")
        
        return None
    
    def get_yahoo_historical(self, metal: Metal = Metal.GOLD,
                             period: str = "6mo", 
                             interval: str = "1d") -> Optional[pd.DataFrame]:
        """
        获取Yahoo Finance历史数据
        """
        if not HAS_YFINANCE:
            return None
        
        try:
            ticker = yf.Ticker(metal.yf_symbol)
            df = ticker.history(period=period, interval=interval)
            
            if not df.empty:
                df = df.dropna()
                df.index = pd.to_datetime(df.index)
                self.current_price = float(df['Close'].iloc[-1])
                self.data_source = "Yahoo Finance"
                self.last_update = datetime.now()
                return df
                
        except Exception as e:
            st.error(f"Yahoo历史数据错误: {e}")
        
        return None
    
    def fetch_from_metals_live(self) -> Optional[Dict[str, float]]:
        """
        Metals.Live API - 完全免费，无需注册
        返回所有贵金属实时价格
        """
        try:
            url = "https://api.metals.live/v1/spot"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                prices = {}
                
                for item in data:
                    name = item.get('name', '').lower()
                    price = float(item.get('price', 0))
                    
                    if name == 'gold':
                        prices['GOLD'] = price
                    elif name == 'silver':
                        prices['SILVER'] = price
                    elif name == 'platinum':
                        prices['PLATINUM'] = price
                    elif name == 'palladium':
                        prices['PALLADIUM'] = price
                
                if prices:
                    self.price_cache.update(prices)
                    self.data_source = "Metals.Live"
                    self.last_update = datetime.now()
                    
                    if 'GOLD' in prices:
                        self.current_price = prices['GOLD']
                    
                    return prices
                    
        except Exception as e:
            st.error(f"Metals.Live错误: {e}")
        
        return None
    
    def fetch_single_metal_live(self, metal_name: str = "gold") -> Optional[float]:
        """
        获取单个贵金属实时价格
        """
        try:
            url = f"https://api.metals.live/v1/spot/{metal_name}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    price = float(data[0].get('price', 0))
                    self.current_price = price
                    self.data_source = "Metals.Live"
                    self.last_update = datetime.now()
                    return price
                    
        except Exception as e:
            st.error(f"Metals.Live单品种错误: {e}")
        
        return None
    
    def fetch_from_freegoldapi(self) -> Optional[Dict]:
        """
        FreeGoldAPI.com - 完全免费，无需API Key
        """
        try:
            url = "https://freegoldapi.com/api/gold/latest"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and 'price' in data:
                    self.current_price = float(data['price'])
                    self.data_source = "FreeGoldAPI"
                    self.last_update = datetime.now()
                    return data
                    
        except Exception as e:
            st.error(f"FreeGoldAPI错误: {e}")
        
        return None
    
    def fetch_from_frankfurter(self) -> Optional[float]:
        """
        Frankfurter API - 完全免费
        通过XAU汇率获取金价
        """
        try:
            url = "https://api.frankfurter.app/latest?from=XAU&to=USD"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'rates' in data and 'USD' in data['rates']:
                    self.current_price = float(data['rates']['USD'])
                    self.data_source = "Frankfurter API"
                    self.last_update = datetime.now()
                    return self.current_price
                    
        except Exception as e:
            st.error(f"Frankfurter错误: {e}")
        
        return None
    
    def fetch_realtime(self, metal: Metal = Metal.GOLD, 
                       verbose: bool = True) -> Tuple[Optional[float], str]:
        """
        智能获取实时价格
        自动选择可用的数据源
        """
        sources = [
            ("Yahoo Finance", lambda: self.fetch_from_yahoo(metal)),
            ("Metals.Live", lambda: self._get_metal_price(metal)),
            ("FreeGoldAPI", lambda: self._get_freegoldapi_price()),
            ("Frankfurter", self.fetch_from_frankfurter),
        ]
        
        for name, fetch_func in sources:
            try:
                price = fetch_func()
                if price and price > 0:
                    return price, name
            except Exception as e:
                continue
        
        return None, "无可用数据源"
    
    def _get_metal_price(self, metal: Metal) -> Optional[float]:
        """从Metals.Live获取指定金属价格"""
        prices = self.fetch_from_metals_live()
        if prices and metal.name in prices:
            return prices[metal.name]
        return None
    
    def _get_freegoldapi_price(self) -> Optional[float]:
        """从FreeGoldAPI获取价格"""
        data = self.fetch_from_freegoldapi()
        if data and 'price' in data:
            return float(data['price'])
        return None
    
    def get_all_prices(self) -> Dict[str, float]:
        """
        获取所有贵金属价格
        """
        prices = self.fetch_from_metals_live()
        
        if not prices:
            prices = {}
            for metal in Metal:
                price = self.fetch_from_yahoo(metal)
                if price:
                    prices[metal.name] = price
        
        return prices or {}
    
    def get_historical_data(self, metal: Metal = Metal.GOLD,
                            period: str = "6mo",
                            interval: str = "1d") -> Optional[pd.DataFrame]:
        """
        获取历史K线数据 (主入口)
        """
        df = self.get_yahoo_historical(metal, period, interval)
        
        if df is not None and not df.empty:
            return df
        
        if metal == Metal.GOLD:
            return self.fetch_freegoldapi_historical()
        
        return None
    
    def fetch_freegoldapi_historical(self, start_date: str = None,
                                      end_date: str = None) -> Optional[pd.DataFrame]:
        """
        获取FreeGoldAPI历史数据
        """
        try:
            url = "https://freegoldapi.com/api/gold/history"
            params = {}
            if start_date:
                params['start'] = start_date
            if end_date:
                params['end'] = end_date
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    df = pd.DataFrame(data)
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    return df
                    
        except Exception as e:
            st.error(f"FreeGoldAPI历史数据错误: {e}")
        
        return None


# ============================================
# 斐波那契分析引擎 (增强版 - 自动识别ABC)
# ============================================

class FibonacciAnalyzer:
    """斐波那契分析引擎 - 支持自动识别A/B/C三点"""
    
    RETRACEMENT = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    EXTENSION = [0, 0.382, 0.618, 1.0, 1.272, 1.382, 1.618, 2.0, 2.618]
    
    COLORS = {
        0: '#00FF00', 0.236: '#7FFF00', 0.382: '#FFFF00',
        0.5: '#FFA500', 0.618: '#FF4500', 0.786: '#FF0000',
        1.0: '#8B0000', 1.272: '#9400D3', 1.382: '#4B0082',
        1.618: '#0000FF', 2.0: '#00CED1', 2.618: '#00FA9A'
    }
    
    DESCRIPTIONS = {
        0: "起点",
        0.236: "23.6% - 极浅回调",
        0.382: "38.2% - 健康回调",
        0.5: "50% - 多空平衡",
        0.618: "61.8% - 黄金分割",
        0.786: "78.6% - 深度回调",
        1.0: "100% - 终点",
        1.272: "127.2% - 扩展目标1",
        1.382: "138.2% - 扩展目标2",
        1.618: "161.8% - 黄金扩展",
        2.0: "200% - 双倍扩展",
        2.618: "261.8% - 极端扩展"
    }
    
    def __init__(self):
        self.df = None
        self.swing_low = None      # A点 - 起涨点
        self.swing_high = None     # B点 - 波段高点
        self.point_c = None        # C点 - 回调低点
        self.swing_low_date = None
        self.swing_high_date = None
        self.point_c_date = None
        self.result = None
    
    def set_data(self, df: pd.DataFrame):
        self.df = df.copy()
    
    def find_swing_points(self, use_pivot: bool = True, pivot_window: int = 5):
        """
        智能识别波段高低点 A/B/C
        
        策略:
        1. 找到历史最高点 B
        2. 在B之前找到最低点 A (起涨点)
        3. 在B之后找到最低点 C (回调低点)
        """
        if self.df is None or self.df.empty:
            return
        
        if use_pivot and len(self.df) > pivot_window * 2 + 1:
            self._find_pivot_points(pivot_window)
        else:
            self._find_simple_points()
    
    def _find_pivot_points(self, window: int = 5):
        """
        使用Pivot Point算法识别波段点
        """
        df = self.df.copy()
        
        # 计算滚动最高/最低
        roll_high = df['High'].rolling(window=window*2+1, center=True).max()
        roll_low = df['Low'].rolling(window=window*2+1, center=True).min()
        
        # 识别Pivot High/Low
        pivot_highs = df[df['High'] == roll_high]['High'].dropna()
        pivot_lows = df[df['Low'] == roll_low]['Low'].dropna()
        
        if len(pivot_highs) == 0 or len(pivot_lows) == 0:
            self._find_simple_points()
            return
        
        # B点: 最近的Pivot High
        self.swing_high_date = pivot_highs.index[-1]
        self.swing_high = float(pivot_highs.iloc[-1])
        
        # A点: B点之前的Pivot Low
        lows_before_b = pivot_lows[pivot_lows.index < self.swing_high_date]
        if len(lows_before_b) > 0:
            self.swing_low_date = lows_before_b.index[-1]
            self.swing_low = float(lows_before_b.iloc[-1])
        else:
            # 如果没有pivot low，使用B点前的最低
            before_b = df.loc[:self.swing_high_date]
            self.swing_low_date = before_b['Low'].idxmin()
            self.swing_low = float(before_b['Low'].min())
        
        # C点: B点之后的Pivot Low 或最近低点
        after_b = df.loc[self.swing_high_date:]
        if len(after_b) > 1:
            # 找B点之后的最低点
            self.point_c_date = after_b['Low'].idxmin()
            self.point_c = float(after_b['Low'].min())
            
            # 如果C点就是B点，使用最新价格作为C
            if self.point_c_date == self.swing_high_date:
                self.point_c_date = df.index[-1]
                self.point_c = float(df['Close'].iloc[-1])
        else:
            self.point_c_date = df.index[-1]
            self.point_c = float(df['Close'].iloc[-1])
    
    def _find_simple_points(self):
        """
        简单方法识别波段点 (不使用pivot)
        """
        df = self.df
        
        # B点: 历史最高点
        self.swing_high_date = df['High'].idxmax()
        self.swing_high = float(df['High'].max())
        
        # A点: B点之前的最低点
        before_b = df.loc[:self.swing_high_date]
        self.swing_low_date = before_b['Low'].idxmin()
        self.swing_low = float(before_b['Low'].min())
        
        # C点: B点之后的最低点
        after_b = df.loc[self.swing_high_date:]
        if len(after_b) > 1:
            self.point_c_date = after_b['Low'].idxmin()
            self.point_c = float(after_b['Low'].min())
        else:
            self.point_c_date = df.index[-1]
            self.point_c = float(df['Close'].iloc[-1])
    
    def calculate_retracement(self, swing_low: float = None, 
                               swing_high: float = None) -> Optional[Dict]:
        """计算斐波那契回调位"""
        low = swing_low or self.swing_low
        high = swing_high or self.swing_high
        
        if not low or not high:
            return None
        
        price_range = high - low
        levels = {}
        
        for level in self.RETRACEMENT:
            price = high - (price_range * level)
            levels[level] = {
                'price': round(price, 2),
                'name': f"{level*100:.1f}%",
                'color': self.COLORS.get(level, '#FFFFFF'),
                'description': self.DESCRIPTIONS.get(level, "")
            }
        
        self.result = {
            'type': 'retracement',
            'swing_low': low,
            'swing_high': high,
            'range': round(price_range, 2),
            'levels': levels
        }
        
        return self.result
    
    def calculate_extension(self, point_a: float = None, 
                            point_b: float = None,
                            point_c: float = None) -> Optional[Dict]:
        """计算斐波那契扩展位"""
        a = point_a or self.swing_low
        b = point_b or self.swing_high
        c = point_c or self.point_c
        
        if not all([a, b, c]):
            return None
        
        ab_range = b - a
        levels = {}
        
        for level in self.EXTENSION:
            price = c + (ab_range * level)
            levels[level] = {
                'price': round(price, 2),
                'name': f"{level*100:.1f}%",
                'color': self.COLORS.get(level, '#FFFFFF'),
                'description': self.DESCRIPTIONS.get(level, "")
            }
        
        self.result = {
            'type': 'extension',
            'point_a': a,
            'point_b': b,
            'point_c': c,
            'ab_range': round(ab_range, 2),
            'levels': levels
        }
        
        return self.result
    
    def get_abc_summary(self) -> Dict:
        """获取ABC三点摘要"""
        return {
            'A': {'date': self.swing_low_date, 'price': self.swing_low},
            'B': {'date': self.swing_high_date, 'price': self.swing_high},
            'C': {'date': self.point_c_date, 'price': self.point_c},
        }


# ============================================
# 技术指标
# ============================================

class TechnicalIndicators:
    """技术指标计算"""
    
    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period).mean()
    
    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, 
                        std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26, 
             signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram


# ============================================
# Streamlit 应用主函数
# ============================================

def init_session_state():
    """初始化session state"""
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'current_price' not in st.session_state:
        st.session_state.current_price = None
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = FibonacciAnalyzer()
    if 'fetcher' not in st.session_state:
        st.session_state.fetcher = FreeGoldFetcher()
    if 'indicators' not in st.session_state:
        st.session_state.indicators = TechnicalIndicators()
    if 'current_metal' not in st.session_state:
        st.session_state.current_metal = Metal.GOLD
    if 'data_source' not in st.session_state:
        st.session_state.data_source = None
    if 'auto_detected' not in st.session_state:
        st.session_state.auto_detected = False


def create_fib_chart(df, analyzer, current_price, metal, show_indicators=True, show_abc=True):
    """创建斐波那契图表"""
    if not HAS_PLOTLY or df is None:
        return None
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{metal.cn_name}价格走势', 'RSI指标')
    )
    
    dates = df.index
    closes = df['Close'].values
    
    # 价格线
    fig.add_trace(
        go.Scatter(
            x=dates, y=closes,
            name=f'{metal.cn_name} 收盘价',
            line=dict(color=metal.color, width=1.5),
            mode='lines'
        ),
        row=1, col=1
    )
    
    # 均线
    if show_indicators:
        ma20 = TechnicalIndicators.sma(df['Close'], 20)
        ma50 = TechnicalIndicators.sma(df['Close'], 50)
        
        fig.add_trace(
            go.Scatter(
                x=dates, y=ma20,
                name='MA20',
                line=dict(color='#FF9800', width=1)
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=dates, y=ma50,
                name='MA50',
                line=dict(color='#2196F3', width=1)
            ),
            row=1, col=1
        )
    
    # 标记 A/B/C 三点
    if show_abc and analyzer.swing_low_date and analyzer.swing_high_date:
        # A点 - 起涨点 (绿色)
        if analyzer.swing_low_date in df.index:
            fig.add_trace(
                go.Scatter(
                    x=[analyzer.swing_low_date],
                    y=[analyzer.swing_low],
                    mode='markers+text',
                    name='A点 (起涨)',
                    marker=dict(size=15, color='#00FF00', symbol='circle'),
                    text=['A'],
                    textposition='bottom center',
                    textfont=dict(size=14, color='#00FF00', weight='bold')
                ),
                row=1, col=1
            )
        
        # B点 - 波段高点 (红色)
        if analyzer.swing_high_date in df.index:
            fig.add_trace(
                go.Scatter(
                    x=[analyzer.swing_high_date],
                    y=[analyzer.swing_high],
                    mode='markers+text',
                    name='B点 (高点)',
                    marker=dict(size=15, color='#FF0000', symbol='circle'),
                    text=['B'],
                    textposition='top center',
                    textfont=dict(size=14, color='#FF0000', weight='bold')
                ),
                row=1, col=1
            )
        
        # C点 - 回调低点 (蓝色)
        if analyzer.point_c_date and analyzer.point_c_date in df.index:
            fig.add_trace(
                go.Scatter(
                    x=[analyzer.point_c_date],
                    y=[analyzer.point_c],
                    mode='markers+text',
                    name='C点 (回调)',
                    marker=dict(size=15, color='#0080FF', symbol='circle'),
                    text=['C'],
                    textposition='bottom center',
                    textfont=dict(size=14, color='#0080FF', weight='bold')
                ),
                row=1, col=1
            )
        
        # 画AB连线
        fig.add_trace(
            go.Scatter(
                x=[analyzer.swing_low_date, analyzer.swing_high_date],
                y=[analyzer.swing_low, analyzer.swing_high],
                mode='lines',
                name='AB波段',
                line=dict(color='rgba(255,255,0,0.5)', width=2, dash='dash')
            ),
            row=1, col=1
        )
    
    # 斐波那契水平
    if analyzer.result:
        for level, info in analyzer.result['levels'].items():
            fig.add_hline(
                y=info['price'],
                line_dash="dash",
                line_color=info['color'],
                line_width=1,
                annotation_text=f"{info['name']} (${info['price']:,.2f})",
                annotation_position="right",
                row=1, col=1
            )
    
    # 当前价格线
    if current_price:
        fig.add_hline(
            y=current_price,
            line_dash="solid",
            line_color='#FFFFFF',
            line_width=2,
            annotation_text=f'当前 ${current_price:,.2f}',
            annotation_position="right",
            row=1, col=1
        )
    
    # RSI指标
    if show_indicators:
        rsi = TechnicalIndicators.rsi(df['Close'])
        fig.add_trace(
            go.Scatter(
                x=dates, y=rsi,
                name='RSI(14)',
                line=dict(color='#E91E63', width=1.5)
            ),
            row=2, col=1
        )
        fig.add_hline(y=70, line_dash="dash", line_color='#FF4444', line_width=1, row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color='#00FF00', line_width=1, row=2, col=1)
        fig.update_yaxes(range=[0, 100], row=2, col=1)
    
    fig.update_layout(
        height=700,
        showlegend=True,
        template='plotly_dark',
        paper_bgcolor='#1a1a2e',
        plot_bgcolor='#16213e',
        font=dict(color='white'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.3)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.3)')
    
    return fig


def update_indicators_text(df):
    """更新技术指标文本"""
    if df is None or df.empty:
        return "无数据"
    
    close = df['Close']
    indicators = TechnicalIndicators()
    
    rsi = indicators.rsi(close).iloc[-1]
    macd_line, signal_line, hist = indicators.macd(close)
    ma20 = indicators.sma(close, 20).iloc[-1]
    ma50 = indicators.sma(close, 50).iloc[-1]
    upper, middle, lower = indicators.bollinger_bands(close)
    
    current = close.iloc[-1]
    
    # 信号判断
    rsi_signal = "🟢 超卖" if rsi < 30 else ("🔴 超买" if rsi > 70 else "⚪ 中性")
    ma_signal = "🟢 多头" if ma20 > ma50 else "🔴 空头"
    macd_signal = "🟢 多头" if macd_line.iloc[-1] > signal_line.iloc[-1] else "🔴 空头"
    
    bb_position = (current - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1]) * 100
    
    text = f"""
╔══════════════════════════════════════════════╗
║           📊 技术指标分析                      ║
╚══════════════════════════════════════════════╝

【动量指标】
  RSI (14):     {rsi:.2f}  {rsi_signal}

【趋势指标】
  MACD:         {macd_line.iloc[-1]:+.4f}  {macd_signal}
  Signal:       {signal_line.iloc[-1]:+.4f}

【均线系统】
  MA20:         ${ma20:,.2f}
  MA50:         ${ma50:,.2f}
  趋势:         {ma_signal}

【布林带】
  上轨:         ${upper.iloc[-1]:,.2f}
  中轨:         ${middle.iloc[-1]:,.2f}
  下轨:         ${lower.iloc[-1]:,.2f}
  当前位置:     {bb_position:.1f}%

══════════════════════════════════════════════
"""
    return text


def generate_signals(current_price, analyzer, metal):
    """生成交易建议"""
    if not current_price or not analyzer.result:
        return "请先获取数据并运行分析"
    
    levels = analyzer.result['levels']
    
    supports = [(l, i) for l, i in levels.items() if i['price'] < current_price]
    resistances = [(l, i) for l, i in levels.items() if i['price'] > current_price]
    
    supports.sort(key=lambda x: x[1]['price'], reverse=True)
    resistances.sort(key=lambda x: x[1]['price'])
    
    # 获取ABC信息
    abc = analyzer.get_abc_summary()
    
    text = f"""
╔════════════════════════════════════════════════╗
║         🎯 {metal.cn_name}交易建议                          
║         {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}              
╚════════════════════════════════════════════════╝

当前价格: ${current_price:,.2f}

【ABC波段分析】
  A点 (起涨):  ${abc['A']['price']:,.2f}  [{abc['A']['date'].strftime('%m-%d') if abc['A']['date'] else '--'}]
  B点 (高点):  ${abc['B']['price']:,.2f}  [{abc['B']['date'].strftime('%m-%d') if abc['B']['date'] else '--'}]
  C点 (回调):  ${abc['C']['price']:,.2f}  [{abc['C']['date'].strftime('%m-%d') if abc['C']['date'] else '--'}]
  
  AB涨幅:      {((abc['B']['price'] - abc['A']['price']) / abc['A']['price'] * 100):.2f}%
  BC回调:      {((abc['B']['price'] - abc['C']['price']) / (abc['B']['price'] - abc['A']['price']) * 100):.1f}%

{'─'*48}
📉 支撑位 (买入区域)
{'─'*48}
"""
    for level, info in supports[:4]:
        dist = current_price - info['price']
        text += f"  • {info['name']:8} ${info['price']:>10,.2f} (-{dist/current_price*100:.1f}%)\n"
    
    text += f"""
{'─'*48}
📈 阻力位 (卖出区域)
{'─'*48}
"""
    for level, info in resistances[:4]:
        dist = info['price'] - current_price
        text += f"  • {info['name']:8} ${info['price']:>10,.2f} (+{dist/current_price*100:.1f}%)\n"
    
    if supports and resistances:
        nearest_sup = supports[0][1]['price']
        nearest_res = resistances[0][1]['price']
        risk = current_price - nearest_sup
        reward = nearest_res - current_price
        rr = reward / risk if risk > 0 else 0
        
        text += f"""
{'─'*48}
📊 风险收益分析
{'─'*48}
  • 潜在风险: ${risk:,.2f} ({risk/current_price*100:.1f}%)
  • 潜在收益: ${reward:,.2f} ({reward/current_price*100:.1f}%)
  • 风险收益比: 1:{rr:.2f}
  • 评估: {'🟢 值得交易' if rr >= 2 else ('🟡 谨慎' if rr >= 1 else '🔴 不建议')}
"""
    
    text += f"""
{'═'*48}
⚠️ 风险提示: 本建议仅供参考，不构成投资建议
{'═'*48}
"""
    return text


def main():
    # 初始化
    init_session_state()
    
    # 标题
    st.title("🥇 黄金斐波那契分析系统 v4.2")
    st.caption("完全免费版 - 无需API Key | 智能识别ABC三点 | 数据源: Yahoo Finance / Metals.Live / FreeGoldAPI / Frankfurter")
    
    # 侧边栏 - 控制面板
    with st.sidebar:
        st.header("⚙️ 控制面板")
        
        # 品种选择
        metal_name = st.selectbox(
            "选择品种",
            [m.name for m in Metal],
            index=0
        )
        st.session_state.current_metal = Metal[metal_name]
        
        # 周期选择
        period = st.selectbox(
            "历史周期",
            ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
            index=2
        )
        
        # 间隔选择
        interval = st.selectbox(
            "数据间隔",
            ["1h", "1d", "1wk", "1mo"],
            index=1
        )
        
        st.divider()
        
        # 智能识别设置
        st.subheader("🔍 智能识别设置")
        use_pivot = st.checkbox("使用Pivot算法", value=True, 
                                help="使用更精确的Pivot Point算法识别波段点")
        pivot_window = st.slider("Pivot窗口", min_value=2, max_value=10, value=5,
                                 help="窗口越大，识别的波段点越少但越重要")
        
        st.divider()
        
        # 斐波那契参数
        st.subheader("📐 斐波那契参数")
        
        # 显示自动识别的值
        analyzer = st.session_state.analyzer
        
        col_a1, col_a2 = st.columns([1, 2])
        with col_a1:
            st.markdown("**A点 (低点)**")
        with col_a2:
            if analyzer.swing_low:
                st.markdown(f"<span style='color:#00FF00'>${analyzer.swing_low:,.2f}</span>", unsafe_allow_html=True)
        
        low_input = st.text_input("A点价格 (覆盖自动值)", value="", 
                                  placeholder=f"自动: {analyzer.swing_low:.2f}" if analyzer.swing_low else "自动",
                                  help="留空使用自动识别的A点")
        
        col_b1, col_b2 = st.columns([1, 2])
        with col_b1:
            st.markdown("**B点 (高点)**")
        with col_b2:
            if analyzer.swing_high:
                st.markdown(f"<span style='color:#FF0000'>${analyzer.swing_high:,.2f}</span>", unsafe_allow_html=True)
        
        high_input = st.text_input("B点价格 (覆盖自动值)", value="",
                                   placeholder=f"自动: {analyzer.swing_high:.2f}" if analyzer.swing_high else "自动",
                                   help="留空使用自动识别的B点")
        
        col_c1, col_c2 = st.columns([1, 2])
        with col_c1:
            st.markdown("**C点 (回调)**")
        with col_c2:
            if analyzer.point_c:
                st.markdown(f"<span style='color:#0080FF'>${analyzer.point_c:,.2f}</span>", unsafe_allow_html=True)
        
        c_input = st.text_input("C点价格 (扩展分析用)", value="",
                                placeholder=f"自动: {analyzer.point_c:.2f}" if analyzer.point_c else "自动",
                                help="留空使用自动识别的C点 (扩展分析需要)")
        
        st.divider()
        
        # 按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 获取数据", type="primary", use_container_width=True):
                with st.spinner("正在获取历史数据..."):
                    metal = st.session_state.current_metal
                    fetcher = st.session_state.fetcher
                    
                    df = fetcher.get_historical_data(metal, period, interval)
                    
                    if df is not None and not df.empty:
                        st.session_state.df = df
                        st.session_state.current_price = float(df['Close'].iloc[-1])
                        st.session_state.data_source = fetcher.data_source
                        
                        # 自动识别波段点
                        analyzer = st.session_state.analyzer
                        analyzer.set_data(df)
                        analyzer.find_swing_points(use_pivot=use_pivot, pivot_window=pivot_window)
                        st.session_state.auto_detected = True
                        
                        st.success(f"✅ 成功获取 {len(df)} 条数据\n🔍 已自动识别ABC三点")
                    else:
                        st.error("❌ 无法获取数据")
        
        with col2:
            if st.button("⚡ 实时价格", type="secondary", use_container_width=True):
                with st.spinner("正在获取实时价格..."):
                    metal = st.session_state.current_metal
                    fetcher = st.session_state.fetcher
                    
                    price, source = fetcher.fetch_realtime(metal, verbose=False)
                    
                    if price:
                        st.session_state.current_price = price
                        st.session_state.data_source = source
                        st.success(f"✅ {source}: ${price:,.2f}")
                    else:
                        st.error("❌ 无法获取实时价格")
        
        st.divider()
        
        # 分析按钮
        st.subheader("📊 分析")
        
        col3, col4 = st.columns(2)
        with col3:
            if st.button("📈 回调分析", type="primary", use_container_width=True):
                analyzer = st.session_state.analyzer
                
                try:
                    swing_low = float(low_input) if low_input else analyzer.swing_low
                    swing_high = float(high_input) if high_input else analyzer.swing_high
                    
                    if swing_low and swing_high:
                        analyzer.calculate_retracement(swing_low, swing_high)
                        st.success("✅ 回调分析完成")
                    else:
                        st.warning("⚠️ 请先获取数据或输入A/B点")
                except ValueError:
                    st.error("❌ 请输入有效数字")
        
        with col4:
            if st.button("🎯 扩展分析", type="primary", use_container_width=True):
                analyzer = st.session_state.analyzer
                
                try:
                    point_a = float(low_input) if low_input else analyzer.swing_low
                    point_b = float(high_input) if high_input else analyzer.swing_high
                    point_c = float(c_input) if c_input else analyzer.point_c
                    
                    if all([point_a, point_b, point_c]):
                        analyzer.calculate_extension(point_a, point_b, point_c)
                        st.success("✅ 扩展分析完成")
                    else:
                        st.warning("⚠️ 扩展分析需要A/B/C三点")
                except ValueError:
                    st.error("❌ 请输入有效数字")
        
        # 一键分析按钮
        if st.button("🚀 一键分析 (自动识别+计算)", use_container_width=True, 
                    help="自动识别ABC三点并执行回调和扩展分析"):
            if st.session_state.df is None:
                st.error("❌ 请先获取数据")
            else:
                analyzer = st.session_state.analyzer
                
                # 确保已识别波段点
                if not st.session_state.auto_detected:
                    analyzer.set_data(st.session_state.df)
                    analyzer.find_swing_points(use_pivot=use_pivot, pivot_window=pivot_window)
                
                # 执行回调分析
                if analyzer.swing_low and analyzer.swing_high:
                    analyzer.calculate_retracement(analyzer.swing_low, analyzer.swing_high)
                    
                    # 执行扩展分析 (如果有C点)
                    if analyzer.point_c:
                        analyzer.calculate_extension(analyzer.swing_low, analyzer.swing_high, analyzer.point_c)
                        st.success("✅ 回调分析 + 扩展分析完成")
                    else:
                        st.success("✅ 回调分析完成 (无C点)")
                else:
                    st.error("❌ 无法识别波段点")
        
        st.divider()
        
        # 显示选项
        st.subheader("👁️ 显示选项")
        show_indicators = st.checkbox("显示技术指标", value=True)
        show_abc = st.checkbox("显示ABC标记", value=True)
    
    # 主内容区
    # 价格信息栏
    metal = st.session_state.current_metal
    current_price = st.session_state.current_price
    data_source = st.session_state.data_source
    analyzer = st.session_state.analyzer
    
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    
    with col1:
        st.metric(
            label=f"🥇 {metal.cn_name} ({metal.api_symbol}/USD)",
            value=f"${current_price:,.2f}" if current_price else "--",
        )
    
    with col2:
        st.metric(
            label="数据源",
            value=data_source if data_source else "--"
        )
    
    with col3:
        st.metric(
            label="更新时间",
            value=datetime.now().strftime('%H:%M:%S')
        )
    
    with col4:
        df = st.session_state.df
        if df is not None:
            st.metric(
                label="数据点",
                value=f"{len(df)} 条"
            )
        else:
            st.metric(label="数据点", value="--")
    
    # ABC三点信息卡片
    if analyzer.swing_low and analyzer.swing_high:
        st.divider()
        abc_cols = st.columns(4)
        
        with abc_cols[0]:
            st.markdown("""
            <div style='background:#1a1a2e;padding:10px;border-radius:5px;border-left:4px solid #00FF00'>
            <b style='color:#00FF00'>A点 (起涨)</b><br>
            <span style='font-size:1.2em'>${:.2f}</span><br>
            <small>{}</small>
            </div>
            """.format(analyzer.swing_low, 
                      analyzer.swing_low_date.strftime('%Y-%m-%d') if analyzer.swing_low_date else '--'), 
                      unsafe_allow_html=True)
        
        with abc_cols[1]:
            st.markdown("""
            <div style='background:#1a1a2e;padding:10px;border-radius:5px;border-left:4px solid #FF0000'>
            <b style='color:#FF0000'>B点 (高点)</b><br>
            <span style='font-size:1.2em'>${:.2f}</span><br>
            <small>{}</small>
            </div>
            """.format(analyzer.swing_high,
                      analyzer.swing_high_date.strftime('%Y-%m-%d') if analyzer.swing_high_date else '--'),
                      unsafe_allow_html=True)
        
        with abc_cols[2]:
            c_price = analyzer.point_c if analyzer.point_c else current_price
            c_date = analyzer.point_c_date if analyzer.point_c_date else (df.index[-1] if df is not None else None)
            st.markdown("""
            <div style='background:#1a1a2e;padding:10px;border-radius:5px;border-left:4px solid #0080FF'>
            <b style='color:#0080FF'>C点 (回调)</b><br>
            <span style='font-size:1.2em'>${:.2f}</span><br>
            <small>{}</small>
            </div>
            """.format(c_price,
                      c_date.strftime('%Y-%m-%d') if c_date else '--'),
                      unsafe_allow_html=True)
        
        with abc_cols[3]:
            if analyzer.swing_low and analyzer.swing_high and analyzer.point_c:
                retracement = (analyzer.swing_high - analyzer.point_c) / (analyzer.swing_high - analyzer.swing_low) * 100
                st.markdown("""
                <div style='background:#1a1a2e;padding:10px;border-radius:5px;border-left:4px solid #FFD700'>
                <b style='color:#FFD700'>BC回调幅度</b><br>
                <span style='font-size:1.2em'>{:.1f}%</span><br>
                <small>of AB波段</small>
                </div>
                """.format(retracement), unsafe_allow_html=True)
    
    st.divider()
    
    # 创建标签页
    tab_chart, tab_levels, tab_signals, tab_indicators = st.tabs([
        "📈 价格图表", "📐 斐波那契水平", "🎯 交易建议", "📊 技术指标"
    ])
    
    # 图表标签页
    with tab_chart:
        df = st.session_state.df
        analyzer = st.session_state.analyzer
        
        if df is not None and HAS_PLOTLY:
            fig = create_fib_chart(df, analyzer, current_price, metal, show_indicators, show_abc)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📥 请点击左侧「获取数据」按钮加载图表")
    
    # 斐波那契水平标签页
    with tab_levels:
        analyzer = st.session_state.analyzer
        
        if analyzer.result:
            levels_data = []
            current = current_price or 0
            
            sorted_levels = sorted(analyzer.result['levels'].items(),
                                   key=lambda x: x[1]['price'], reverse=True)
            
            for level, info in sorted_levels:
                price = info['price']
                distance = price - current
                
                if current > 0:
                    pct = distance / current * 100
                    dist_str = f"{'+' if distance >= 0 else ''}${distance:,.0f} ({pct:+.1f}%)"
                else:
                    dist_str = "--"
                
                level_type = "阻力" if distance > 0 else "支撑"
                
                levels_data.append({
                    "水平": info['name'],
                    "价格": f"${price:,.2f}",
                    "距离": dist_str,
                    "类型": level_type,
                    "说明": info['description']
                })
            
            levels_df = pd.DataFrame(levels_data)
            st.dataframe(levels_df, use_container_width=True, hide_index=True)
        else:
            st.info("🔍 请先运行回调分析或扩展分析")
    
    # 交易建议标签页
    with tab_signals:
        analyzer = st.session_state.analyzer
        
        if analyzer.result:
            signals_text = generate_signals(current_price, analyzer, metal)
            st.text(signals_text)
        else:
            st.info("🔍 请先运行分析以生成交易建议")
    
    # 技术指标标签页
    with tab_indicators:
        df = st.session_state.df
        
        if df is not None:
            indicators_text = update_indicators_text(df)
            st.text(indicators_text)
        else:
            st.info("📥 请先获取数据")
    
    # 页脚
    st.divider()
    st.caption("""
    ⚠️ **风险提示**: 本工具仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。
    
    📡 **数据源**: Yahoo Finance (yfinance) | Metals.Live API | FreeGoldAPI.com | Frankfurter API
    
    🔍 **智能识别**: 使用Pivot Point算法自动识别ABC三点，支持斐波那契回调和扩展分析
    """)


if __name__ == "__main__":
    main()
