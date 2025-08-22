#!/usr/bin/env python3
"""
交易日志系统 - 完整的交易记录、分析和报告
支持实时日志记录、性能分析、AI决策追溯和风险事件监控
"""

import json
import csv
import sqlite3
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class TradeRecord:
    """交易记录"""
    trade_id: str
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    entry_time: float = 0.0
    exit_time: Optional[float] = None
    realized_pnl: Optional[float] = None
    fees: float = 0.0
    leverage: float = 1.0
    margin_used: float = 0.0
    max_adverse_move: float = 0.0
    max_favorable_move: float = 0.0
    holding_duration: Optional[float] = None
    exit_reason: str = "manual"  # "manual", "stop_loss", "take_profit", "liquidation"
    strategy: str = "manual"
    ai_decision_id: Optional[str] = None
    notes: str = ""
    
    def __post_init__(self):
        if self.entry_time == 0.0:
            self.entry_time = time.time()
        if self.trade_id == "":
            self.trade_id = str(uuid.uuid4())[:8]

@dataclass
class AIDecisionRecord:
    """AI决策记录"""
    decision_id: str
    timestamp: float
    symbol: str
    model_used: str
    analysis_type: str  # "vpa", "trading_signal", "quick", etc.
    raw_analysis: str
    extracted_signals: Dict[str, Any]
    confidence_score: Optional[float] = None
    consensus_data: Optional[Dict[str, Any]] = None
    market_conditions: Optional[Dict[str, Any]] = None
    recommendation: str = ""
    risk_assessment: str = ""
    
    def __post_init__(self):
        if self.decision_id == "":
            self.decision_id = str(uuid.uuid4())[:8]

@dataclass
class RiskEvent:
    """风险事件"""
    event_id: str
    timestamp: float
    event_type: str  # "margin_call", "liquidation", "stop_loss", "drawdown"
    symbol: Optional[str] = None
    severity: str = "medium"  # "low", "medium", "high", "critical"
    description: str = ""
    impact: float = 0.0
    action_taken: str = ""
    
    def __post_init__(self):
        if self.event_id == "":
            self.event_id = str(uuid.uuid4())[:8]

class TradeLogger:
    """
    交易日志系统
    
    功能特性:
    - 实时交易记录
    - AI决策追溯
    - 风险事件监控
    - 性能分析和报告
    - 多格式输出(JSON, CSV, SQLite)
    """
    
    def __init__(self, log_dir: str = "logs", db_path: Optional[str] = None):
        """
        初始化交易日志系统
        
        Args:
            log_dir: 日志文件目录
            db_path: SQLite数据库路径
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 数据库设置
        self.db_path = db_path or str(self.log_dir / "trading_database.db")
        self._init_database()
        
        # 内存缓存
        self.active_trades: Dict[str, TradeRecord] = {}
        self.ai_decisions: Dict[str, AIDecisionRecord] = {}
        self.risk_events: List[RiskEvent] = []
        
        # 统计缓存
        self._performance_cache: Optional[Dict[str, Any]] = None
        self._cache_updated = 0.0
        
        logger.info(f"交易日志系统初始化完成 - 日志目录: {self.log_dir}")
    
    def _init_database(self) -> None:
        """初始化数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 交易记录表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        trade_id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        entry_price REAL NOT NULL,
                        exit_price REAL,
                        entry_time REAL NOT NULL,
                        exit_time REAL,
                        realized_pnl REAL,
                        fees REAL DEFAULT 0,
                        leverage REAL DEFAULT 1,
                        margin_used REAL DEFAULT 0,
                        max_adverse_move REAL DEFAULT 0,
                        max_favorable_move REAL DEFAULT 0,
                        holding_duration REAL,
                        exit_reason TEXT DEFAULT 'manual',
                        strategy TEXT DEFAULT 'manual',
                        ai_decision_id TEXT,
                        notes TEXT DEFAULT ''
                    )
                """)
                
                # AI决策记录表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ai_decisions (
                        decision_id TEXT PRIMARY KEY,
                        timestamp REAL NOT NULL,
                        symbol TEXT NOT NULL,
                        model_used TEXT NOT NULL,
                        analysis_type TEXT NOT NULL,
                        raw_analysis TEXT NOT NULL,
                        extracted_signals TEXT,
                        confidence_score REAL,
                        consensus_data TEXT,
                        market_conditions TEXT,
                        recommendation TEXT DEFAULT '',
                        risk_assessment TEXT DEFAULT ''
                    )
                """)
                
                # 风险事件表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS risk_events (
                        event_id TEXT PRIMARY KEY,
                        timestamp REAL NOT NULL,
                        event_type TEXT NOT NULL,
                        symbol TEXT,
                        severity TEXT DEFAULT 'medium',
                        description TEXT DEFAULT '',
                        impact REAL DEFAULT 0,
                        action_taken TEXT DEFAULT ''
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
            raise
    
    def log_trade_entry(self, symbol: str, side: str, quantity: float, 
                       entry_price: float, leverage: float = 1.0,
                       margin_used: float = 0.0, strategy: str = "manual",
                       ai_decision_id: Optional[str] = None) -> str:
        """
        记录开仓交易
        
        Returns:
            交易ID
        """
        try:
            trade = TradeRecord(
                trade_id="",  # 自动生成
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=entry_price,
                leverage=leverage,
                margin_used=margin_used,
                strategy=strategy,
                ai_decision_id=ai_decision_id
            )
            
            self.active_trades[trade.trade_id] = trade
            
            # 保存到数据库
            self._save_trade_to_db(trade)
            
            # 保存到JSON文件
            self._save_to_json_file(trade, "trades")
            
            logger.info(f"记录开仓: {trade.trade_id} - {side} {quantity} {symbol} @ {entry_price}")
            
            return trade.trade_id
            
        except Exception as e:
            logger.error(f"记录开仓失败: {e}")
            return ""
    
    def log_trade_exit(self, trade_id: str, exit_price: float, 
                      realized_pnl: float, fees: float = 0.0,
                      exit_reason: str = "manual", notes: str = "") -> bool:
        """
        记录平仓交易
        
        Returns:
            是否成功
        """
        try:
            if trade_id not in self.active_trades:
                logger.error(f"交易ID不存在: {trade_id}")
                return False
            
            trade = self.active_trades[trade_id]
            
            # 更新交易记录
            trade.exit_price = exit_price
            trade.exit_time = time.time()
            trade.realized_pnl = realized_pnl
            trade.fees = fees
            trade.exit_reason = exit_reason
            trade.notes = notes
            trade.holding_duration = trade.exit_time - trade.entry_time
            
            # 更新数据库
            self._update_trade_in_db(trade)
            
            # 保存到JSON文件
            self._save_to_json_file(trade, "trades")
            
            # 移出活跃交易
            del self.active_trades[trade_id]
            
            # 清理性能缓存
            self._performance_cache = None
            
            logger.info(f"记录平仓: {trade_id} - 盈亏: ${realized_pnl:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"记录平仓失败: {e}")
            return False
    
    def log_ai_decision(self, symbol: str, model_used: str, analysis_type: str,
                       raw_analysis: str, extracted_signals: Dict[str, Any],
                       confidence_score: Optional[float] = None,
                       consensus_data: Optional[Dict[str, Any]] = None,
                       market_conditions: Optional[Dict[str, Any]] = None) -> str:
        """
        记录AI决策
        
        Returns:
            决策ID
        """
        try:
            decision = AIDecisionRecord(
                decision_id="",  # 自动生成
                timestamp=time.time(),
                symbol=symbol,
                model_used=model_used,
                analysis_type=analysis_type,
                raw_analysis=raw_analysis,
                extracted_signals=extracted_signals,
                confidence_score=confidence_score,
                consensus_data=consensus_data,
                market_conditions=market_conditions
            )
            
            self.ai_decisions[decision.decision_id] = decision
            
            # 保存到数据库
            self._save_ai_decision_to_db(decision)
            
            # 保存到JSON文件
            self._save_to_json_file(decision, "ai_decisions")
            
            logger.info(f"记录AI决策: {decision.decision_id} - {model_used} {analysis_type}")
            
            return decision.decision_id
            
        except Exception as e:
            logger.error(f"记录AI决策失败: {e}")
            return ""
    
    def log_risk_event(self, event_type: str, symbol: Optional[str] = None,
                      severity: str = "medium", description: str = "",
                      impact: float = 0.0, action_taken: str = "") -> str:
        """
        记录风险事件
        
        Returns:
            事件ID
        """
        try:
            event = RiskEvent(
                event_id="",  # 自动生成
                timestamp=time.time(),
                event_type=event_type,
                symbol=symbol,
                severity=severity,
                description=description,
                impact=impact,
                action_taken=action_taken
            )
            
            self.risk_events.append(event)
            
            # 保存到数据库
            self._save_risk_event_to_db(event)
            
            # 保存到JSON文件
            self._save_to_json_file(event, "risk_events")
            
            logger.warning(f"风险事件: {event_type} - {severity} - {description}")
            
            return event.event_id
            
        except Exception as e:
            logger.error(f"记录风险事件失败: {e}")
            return ""
    
    def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        获取交易性能摘要
        
        Args:
            days: 统计天数
            
        Returns:
            性能摘要
        """
        try:
            # 检查缓存
            if (self._performance_cache and 
                time.time() - self._cache_updated < 300):  # 5分钟缓存
                return self._performance_cache
            
            since_timestamp = time.time() - (days * 24 * 3600)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 查询已完成的交易
                cursor.execute("""
                    SELECT * FROM trades 
                    WHERE exit_time IS NOT NULL AND exit_time > ?
                    ORDER BY exit_time DESC
                """, (since_timestamp,))
                
                trades = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                if not trades:
                    return {'error': '没有完成的交易记录'}
                
                # 转换为字典列表
                trade_dicts = [dict(zip(columns, trade)) for trade in trades]
                
                # 计算统计指标
                total_trades = len(trade_dicts)
                winning_trades = len([t for t in trade_dicts if t['realized_pnl'] > 0])
                losing_trades = total_trades - winning_trades
                
                total_pnl = sum(t['realized_pnl'] for t in trade_dicts)
                total_fees = sum(t['fees'] for t in trade_dicts)
                
                win_rate = winning_trades / total_trades if total_trades > 0 else 0
                
                # 计算最大盈亏
                max_win = max([t['realized_pnl'] for t in trade_dicts], default=0)
                max_loss = min([t['realized_pnl'] for t in trade_dicts], default=0)
                
                # 计算平均持仓时间
                avg_holding_time = sum([t['holding_duration'] or 0 for t in trade_dicts]) / total_trades
                
                # 计算连续盈亏
                current_streak = 0
                max_win_streak = 0
                max_loss_streak = 0
                temp_win_streak = 0
                temp_loss_streak = 0
                
                for trade in reversed(trade_dicts):
                    if trade['realized_pnl'] > 0:
                        temp_win_streak += 1
                        temp_loss_streak = 0
                        if current_streak == 0:
                            current_streak = temp_win_streak
                    else:
                        temp_loss_streak += 1
                        temp_win_streak = 0
                        if current_streak == 0:
                            current_streak = -temp_loss_streak
                    
                    max_win_streak = max(max_win_streak, temp_win_streak)
                    max_loss_streak = max(max_loss_streak, temp_loss_streak)
                
                # 按策略分组统计
                strategy_stats = {}
                for trade in trade_dicts:
                    strategy = trade['strategy']
                    if strategy not in strategy_stats:
                        strategy_stats[strategy] = {
                            'trades': 0,
                            'wins': 0,
                            'total_pnl': 0.0
                        }
                    
                    strategy_stats[strategy]['trades'] += 1
                    if trade['realized_pnl'] > 0:
                        strategy_stats[strategy]['wins'] += 1
                    strategy_stats[strategy]['total_pnl'] += trade['realized_pnl']
                
                # 计算每个策略的胜率
                for strategy in strategy_stats:
                    stats = strategy_stats[strategy]
                    stats['win_rate'] = stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0
                
                summary = {
                    'period_days': days,
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate,
                    'total_pnl': total_pnl,
                    'total_fees': total_fees,
                    'net_pnl': total_pnl - total_fees,
                    'max_win': max_win,
                    'max_loss': max_loss,
                    'avg_holding_time_hours': avg_holding_time / 3600,
                    'current_streak': current_streak,
                    'max_win_streak': max_win_streak,
                    'max_loss_streak': max_loss_streak,
                    'strategy_breakdown': strategy_stats
                }
                
                # 缓存结果
                self._performance_cache = summary
                self._cache_updated = time.time()
                
                return summary
                
        except Exception as e:
            logger.error(f"获取性能摘要失败: {e}")
            return {'error': str(e)}
    
    def export_to_csv(self, table: str = "trades", days: int = 30) -> str:
        """
        导出数据到CSV文件
        
        Args:
            table: 表名 ("trades", "ai_decisions", "risk_events")
            days: 导出天数
            
        Returns:
            CSV文件路径
        """
        try:
            since_timestamp = time.time() - (days * 24 * 3600)
            today = datetime.now().strftime("%Y%m%d")
            csv_path = self.log_dir / f"{table}_{today}.csv"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if table == "trades":
                    cursor.execute("SELECT * FROM trades WHERE entry_time > ? ORDER BY entry_time DESC", 
                                 (since_timestamp,))
                elif table == "ai_decisions":
                    cursor.execute("SELECT * FROM ai_decisions WHERE timestamp > ? ORDER BY timestamp DESC",
                                 (since_timestamp,))
                elif table == "risk_events":
                    cursor.execute("SELECT * FROM risk_events WHERE timestamp > ? ORDER BY timestamp DESC",
                                 (since_timestamp,))
                else:
                    raise ValueError(f"未知表名: {table}")
                
                data = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                if not data:
                    return ""
                
                with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(columns)
                    writer.writerows(data)
                
                logger.info(f"数据已导出到: {csv_path}")
                return str(csv_path)
                
        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            return ""
    
    def generate_daily_report(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        生成日报
        
        Args:
            date: 日期 (YYYY-MM-DD)，默认今天
            
        Returns:
            日报数据
        """
        try:
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            
            # 计算时间范围
            start_time = datetime.strptime(date, "%Y-%m-%d").timestamp()
            end_time = start_time + 24 * 3600
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 当日交易统计
                cursor.execute("""
                    SELECT COUNT(*) as total_trades,
                           SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                           SUM(realized_pnl) as total_pnl,
                           SUM(fees) as total_fees
                    FROM trades 
                    WHERE exit_time BETWEEN ? AND ? AND exit_time IS NOT NULL
                """, (start_time, end_time))
                
                trade_stats = cursor.fetchone()
                
                # AI决策统计
                cursor.execute("""
                    SELECT COUNT(*) as total_decisions,
                           COUNT(DISTINCT model_used) as models_used,
                           AVG(confidence_score) as avg_confidence
                    FROM ai_decisions
                    WHERE timestamp BETWEEN ? AND ?
                """, (start_time, end_time))
                
                ai_stats = cursor.fetchone()
                
                # 风险事件统计
                cursor.execute("""
                    SELECT event_type, severity, COUNT(*) as count
                    FROM risk_events
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY event_type, severity
                """, (start_time, end_time))
                
                risk_events = cursor.fetchall()
                
                report = {
                    'date': date,
                    'trading_summary': {
                        'total_trades': trade_stats[0] if trade_stats else 0,
                        'winning_trades': trade_stats[1] if trade_stats else 0,
                        'win_rate': trade_stats[1] / trade_stats[0] if trade_stats and trade_stats[0] > 0 else 0,
                        'total_pnl': trade_stats[2] if trade_stats else 0,
                        'total_fees': trade_stats[3] if trade_stats else 0,
                        'net_pnl': (trade_stats[2] - trade_stats[3]) if trade_stats else 0
                    },
                    'ai_analysis': {
                        'total_decisions': ai_stats[0] if ai_stats else 0,
                        'models_used': ai_stats[1] if ai_stats else 0,
                        'avg_confidence': ai_stats[2] if ai_stats else 0
                    },
                    'risk_events': [
                        {'type': event[0], 'severity': event[1], 'count': event[2]}
                        for event in risk_events
                    ],
                    'generated_at': time.time()
                }
                
                # 保存日报
                report_path = self.log_dir / f"daily_report_{date.replace('-', '')}.json"
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                
                return report
                
        except Exception as e:
            logger.error(f"生成日报失败: {e}")
            return {'error': str(e)}
    
    def _save_trade_to_db(self, trade: TradeRecord) -> None:
        """保存交易到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO trades VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    trade.trade_id, trade.symbol, trade.side, trade.quantity,
                    trade.entry_price, trade.exit_price, trade.entry_time, trade.exit_time,
                    trade.realized_pnl, trade.fees, trade.leverage, trade.margin_used,
                    trade.max_adverse_move, trade.max_favorable_move, trade.holding_duration,
                    trade.exit_reason, trade.strategy, trade.ai_decision_id, trade.notes
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"保存交易到数据库失败: {e}")
    
    def _update_trade_in_db(self, trade: TradeRecord) -> None:
        """更新数据库中的交易记录"""
        self._save_trade_to_db(trade)  # INSERT OR REPLACE
    
    def _save_ai_decision_to_db(self, decision: AIDecisionRecord) -> None:
        """保存AI决策到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO ai_decisions VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    decision.decision_id, decision.timestamp, decision.symbol,
                    decision.model_used, decision.analysis_type, decision.raw_analysis,
                    json.dumps(decision.extracted_signals) if decision.extracted_signals else None,
                    decision.confidence_score,
                    json.dumps(decision.consensus_data) if decision.consensus_data else None,
                    json.dumps(decision.market_conditions) if decision.market_conditions else None,
                    decision.recommendation, decision.risk_assessment
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"保存AI决策到数据库失败: {e}")
    
    def _save_risk_event_to_db(self, event: RiskEvent) -> None:
        """保存风险事件到数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO risk_events VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    event.event_id, event.timestamp, event.event_type,
                    event.symbol, event.severity, event.description,
                    event.impact, event.action_taken
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"保存风险事件到数据库失败: {e}")
    
    def _save_to_json_file(self, record: Union[TradeRecord, AIDecisionRecord, RiskEvent], 
                          record_type: str) -> None:
        """保存记录到JSON文件"""
        try:
            today = datetime.now().strftime("%Y%m%d")
            json_path = self.log_dir / f"{record_type}_{today}.json"
            
            # 读取现有数据
            records = []
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    records = json.load(f)
            
            # 添加新记录
            record_dict = asdict(record)
            # 处理datetime对象
            datetime_keys = []
            for key, value in record_dict.items():
                if isinstance(value, float) and key.endswith('_time'):
                    datetime_keys.append(key)
            
            for key in datetime_keys:
                record_dict[key + '_iso'] = datetime.fromtimestamp(record_dict[key], tz=timezone.utc).isoformat()
            
            records.append(record_dict)
            
            # 保存更新后的数据
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
    
    def cleanup_old_logs(self, days_to_keep: int = 90) -> None:
        """清理旧日志文件"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.strftime("%Y%m%d")
            
            for file_path in self.log_dir.glob("*.json"):
                # 提取日期部分
                filename = file_path.stem
                if "_" in filename:
                    date_part = filename.split("_")[-1]
                    if len(date_part) == 8 and date_part.isdigit():
                        if date_part < cutoff_str:
                            file_path.unlink()
                            logger.info(f"删除旧日志文件: {file_path}")
            
            # 清理数据库中的旧记录
            cutoff_timestamp = cutoff_date.timestamp()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM trades WHERE entry_time < ?", (cutoff_timestamp,))
                cursor.execute("DELETE FROM ai_decisions WHERE timestamp < ?", (cutoff_timestamp,))
                cursor.execute("DELETE FROM risk_events WHERE timestamp < ?", (cutoff_timestamp,))
                conn.commit()
            
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")