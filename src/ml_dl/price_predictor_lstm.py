#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LSTM价格预测模型
使用深度学习预测BTC价格走势
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
import numpy as np

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 尝试导入深度学习库
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("警告: PyTorch未安装，LSTM功能不可用", file=sys.stderr)
    print("请安装: pip install torch", file=sys.stderr)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


class PriceDataset(Dataset):
    """价格数据集"""
    
    def __init__(self, sequences: np.ndarray, targets: np.ndarray):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


class LSTMPredictor(nn.Module):
    """LSTM价格预测模型"""
    
    def __init__(self, input_size: int = 5, hidden_size: int = 64, 
                 num_layers: int = 2, dropout: float = 0.2):
        super(LSTMPredictor, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM层
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True
        )
        
        # 全连接层
        self.fc = nn.Linear(hidden_size, 1)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        # x shape: (batch, seq_len, input_size)
        lstm_out, _ = self.lstm(x)
        # 取最后一个时间步的输出
        last_output = lstm_out[:, -1, :]
        last_output = self.dropout(last_output)
        output = self.fc(last_output)
        return output


class BTCPricePredictor:
    """BTC价格预测器"""
    
    def __init__(self, model_dir: Optional[Path] = None):
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch未安装，无法使用LSTM预测")
        
        if model_dir is None:
            base_dir = Path(__file__).parent.parent.parent
            model_dir = base_dir / "trading_signals" / ".ml_models" / "price_predictor"
        
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.model = None
        self.scaler = None
        self.sequence_length = 60  # 使用60个5分钟K线（5小时）预测
        self.prediction_horizon = 12  # 预测未来12个5分钟（1小时）
        
    def load_price_data(self, start_date: Optional[datetime] = None, 
                       end_date: Optional[datetime] = None) -> pd.DataFrame:
        """从时序库加载价格数据"""
        import duckdb
        
        ts_file = Path(__file__).parent.parent / "data" / "btc_price_timeseries.duckdb"
        if not ts_file.exists():
            raise FileNotFoundError(f"时序库不存在: {ts_file}")
        
        conn = duckdb.connect(str(ts_file))
        
        query = '''
            SELECT timestamp, datetime, open, high, low, close, volume
            FROM btc_price_5m
            ORDER BY timestamp
        '''
        
        if start_date:
            start_ts = int(start_date.timestamp())
            query += f' WHERE timestamp >= {start_ts}'
        
        if end_date:
            end_ts = int(end_date.timestamp())
            if 'WHERE' in query:
                query += f' AND timestamp <= {end_ts}'
            else:
                query += f' WHERE timestamp <= {end_ts}'
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        return df
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备特征"""
        # 计算技术指标
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=20).std()
        
        # 移动平均线
        df['ma_5'] = df['close'].rolling(window=5).mean()
        df['ma_20'] = df['close'].rolling(window=20).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 填充NaN
        df = df.fillna(method='bfill').fillna(0)
        
        return df
    
    def create_sequences(self, data: np.ndarray, seq_length: int, 
                        pred_horizon: int) -> Tuple[np.ndarray, np.ndarray]:
        """创建时间序列数据"""
        X, y = [], []
        
        for i in range(len(data) - seq_length - pred_horizon + 1):
            X.append(data[i:i+seq_length])
            # 预测未来pred_horizon个时间点的平均价格
            y.append(data[i+seq_length:i+seq_length+pred_horizon, 3].mean())  # close价格
        
        return np.array(X), np.array(y)
    
    def train(self, df: pd.DataFrame, epochs: int = 50, batch_size: int = 32,
              learning_rate: float = 0.001):
        """训练模型"""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas未安装")
        
        # 准备特征
        feature_cols = ['open', 'high', 'low', 'close', 'volume', 
                       'returns', 'volatility', 'ma_5', 'ma_20', 'rsi']
        available_cols = [col for col in feature_cols if col in df.columns]
        
        # 标准化
        from sklearn.preprocessing import StandardScaler
        self.scaler = StandardScaler()
        scaled_data = self.scaler.fit_transform(df[available_cols].values)
        
        # 创建序列
        X, y = self.create_sequences(scaled_data, self.sequence_length, self.prediction_horizon)
        
        # 划分训练集和验证集
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # 创建数据加载器
        train_dataset = PriceDataset(X_train, y_train)
        val_dataset = PriceDataset(X_val, y_val)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        # 初始化模型
        input_size = len(available_cols)
        self.model = LSTMPredictor(input_size=input_size, hidden_size=64, num_layers=2)
        
        # 损失函数和优化器
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)
        
        # 训练
        best_val_loss = float('inf')
        train_losses = []
        val_losses = []
        
        print(f"开始训练，训练集: {len(X_train)}, 验证集: {len(X_val)}")
        
        for epoch in range(epochs):
            # 训练阶段
            self.model.train()
            train_loss = 0
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = self.model(batch_X).squeeze()
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
            
            train_loss /= len(train_loader)
            
            # 验证阶段
            self.model.eval()
            val_loss = 0
            with torch.no_grad():
                for batch_X, batch_y in val_loader:
                    outputs = self.model(batch_X).squeeze()
                    loss = criterion(outputs, batch_y)
                    val_loss += loss.item()
            
            val_loss /= len(val_loader)
            scheduler.step(val_loss)
            
            train_losses.append(train_loss)
            val_losses.append(val_loss)
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{epochs}, Train Loss: {train_loss:.6f}, Val Loss: {val_loss:.6f}")
            
            # 保存最佳模型
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                self.save_model()
        
        return {
            'train_losses': train_losses,
            'val_losses': val_losses,
            'best_val_loss': best_val_loss
        }
    
    def predict(self, df: pd.DataFrame, steps: int = 12) -> np.ndarray:
        """预测未来价格"""
        if self.model is None:
            self.load_model()
        
        if self.model is None:
            raise ValueError("模型未训练或加载失败")
        
        # 准备特征
        feature_cols = ['open', 'high', 'low', 'close', 'volume', 
                       'returns', 'volatility', 'ma_5', 'ma_20', 'rsi']
        available_cols = [col for col in feature_cols if col in df.columns]
        
        # 标准化
        scaled_data = self.scaler.transform(df[available_cols].values)
        
        # 取最后sequence_length个数据点
        last_sequence = scaled_data[-self.sequence_length:]
        
        # 预测
        self.model.eval()
        with torch.no_grad():
            input_tensor = torch.FloatTensor(last_sequence).unsqueeze(0)
            prediction = self.model(input_tensor).item()
        
        return prediction
    
    def save_model(self):
        """保存模型"""
        if self.model is None:
            return
        
        model_path = self.model_dir / "lstm_model.pth"
        scaler_path = self.model_dir / "scaler.pkl"
        
        torch.save(self.model.state_dict(), model_path)
        
        import joblib
        joblib.dump(self.scaler, scaler_path)
        
        # 保存元数据
        metadata = {
            'sequence_length': self.sequence_length,
            'prediction_horizon': self.prediction_horizon,
            'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        import json
        metadata_path = self.model_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def load_model(self):
        """加载模型"""
        model_path = self.model_dir / "lstm_model.pth"
        scaler_path = self.model_dir / "scaler.pkl"
        
        if not model_path.exists() or not scaler_path.exists():
            return False
        
        import joblib
        self.scaler = joblib.load(scaler_path)
        
        # 加载元数据
        metadata_path = self.model_dir / "metadata.json"
        if metadata_path.exists():
            import json
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                self.sequence_length = metadata.get('sequence_length', 60)
                self.prediction_horizon = metadata.get('prediction_horizon', 12)
        
        # 初始化模型（需要知道input_size）
        # 这里简化处理，假设input_size=10
        self.model = LSTMPredictor(input_size=10, hidden_size=64, num_layers=2)
        self.model.load_state_dict(torch.load(model_path))
        self.model.eval()
        
        return True


def main():
    """主函数"""
    if not TORCH_AVAILABLE:
        print("❌ PyTorch未安装，请先安装: pip install torch")
        return
    
    print("=" * 80)
    print("LSTM BTC价格预测模型")
    print("=" * 80)
    print()
    
    predictor = BTCPricePredictor()
    
    # 加载数据
    print("加载价格数据...")
    df = predictor.load_price_data()
    print(f"✓ 加载了 {len(df)} 条价格数据")
    
    # 准备特征
    print("准备特征...")
    df = predictor.prepare_features(df)
    print(f"✓ 特征准备完成")
    
    # 训练模型
    print()
    print("开始训练模型...")
    result = predictor.train(df, epochs=50, batch_size=32)
    
    print()
    print("=" * 80)
    print("训练完成！")
    print("=" * 80)
    print(f"最佳验证损失: {result['best_val_loss']:.6f}")
    print()
    
    # 测试预测
    print("测试预测...")
    prediction = predictor.predict(df)
    current_price = df['close'].iloc[-1]
    print(f"当前价格: ${current_price:,.2f}")
    print(f"预测未来1小时平均价格: ${prediction:,.2f}")
    print(f"预测变化: {((prediction - current_price) / current_price * 100):.2f}%")

if __name__ == '__main__':
    main()










