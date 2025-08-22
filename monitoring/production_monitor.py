#!/usr/bin/env python3
"""
ETH永续合约AI分析助手 - 生产环境监控系统
功能：
1. 实时性能监控
2. 成本追踪
3. 错误率统计
4. 自动报警
"""

import time
import json
import logging
import psutil
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class ProductionMonitor:
    """生产环境监控器"""
    
    def __init__(self, config_file='monitoring/monitor_config.json'):
        self.config_file = config_file
        self.load_config()
        self.setup_logging()
        self.metrics = {
            'start_time': datetime.now(),
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_cost': 0.0,
            'average_response_time': 0.0,
            'last_request_time': None
        }
        
    def load_config(self):
        """加载监控配置"""
        default_config = {
            'monitor_interval': 300,  # 5分钟
            'max_daily_cost': 50.0,
            'max_hourly_requests': 100,
            'alert_thresholds': {
                'error_rate': 0.1,  # 10%错误率
                'response_time': 60.0,  # 60秒响应时间
                'memory_usage': 0.85  # 85%内存使用
            },
            'log_retention_days': 7
        }
        
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.config = {**default_config, **config}
            else:
                self.config = default_config
                self.save_config()
        except Exception as e:
            print(f"配置加载失败，使用默认配置: {e}")
            self.config = default_config
    
    def save_config(self):
        """保存配置"""
        try:
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"配置保存失败: {e}")
    
    def setup_logging(self):
        """设置日志"""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU和内存使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': round(memory.used / 1024**3, 2),
                'memory_total_gb': round(memory.total / 1024**3, 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / 1024**3, 2)
            }
        except ImportError:
            # 如果psutil不可用，返回基础指标
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': 0,
                'memory_percent': 0,
                'memory_used_gb': 0,
                'memory_total_gb': 0,
                'disk_percent': 0,
                'disk_free_gb': 0,
                'note': 'psutil not available, using placeholder values'
            }
    
    def collect_app_metrics(self):
        """收集应用指标"""
        uptime = datetime.now() - self.metrics['start_time']
        error_rate = (self.metrics['failed_requests'] / 
                     max(self.metrics['total_requests'], 1))
        
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': uptime.total_seconds(),
            'total_requests': self.metrics['total_requests'],
            'successful_requests': self.metrics['successful_requests'],
            'failed_requests': self.metrics['failed_requests'],
            'error_rate': round(error_rate, 4),
            'total_cost': round(self.metrics['total_cost'], 4),
            'average_response_time': round(self.metrics['average_response_time'], 2),
            'last_request_time': self.metrics['last_request_time'].isoformat() 
                                if self.metrics['last_request_time'] else None
        }
    
    def check_alerts(self, system_metrics, app_metrics):
        """检查告警条件"""
        alerts = []
        thresholds = self.config['alert_thresholds']
        
        # 错误率告警
        if app_metrics['error_rate'] > thresholds['error_rate']:
            alerts.append(f"高错误率: {app_metrics['error_rate']:.2%} > {thresholds['error_rate']:.2%}")
        
        # 响应时间告警
        if app_metrics['average_response_time'] > thresholds['response_time']:
            alerts.append(f"响应时间过长: {app_metrics['average_response_time']:.1f}s > {thresholds['response_time']:.1f}s")
        
        # 内存使用告警
        if system_metrics['memory_percent'] > thresholds['memory_usage'] * 100:
            alerts.append(f"内存使用过高: {system_metrics['memory_percent']:.1f}% > {thresholds['memory_usage']*100:.1f}%")
        
        # 成本告警
        if app_metrics['total_cost'] > self.config['max_daily_cost']:
            alerts.append(f"日成本超限: ${app_metrics['total_cost']:.2f} > ${self.config['max_daily_cost']:.2f}")
        
        return alerts
    
    def log_metrics(self, system_metrics, app_metrics):
        """记录指标"""
        metrics_data = {
            'system': system_metrics,
            'application': app_metrics,
            'timestamp': datetime.now().isoformat()
        }
        
        # 保存到文件
        metrics_file = Path('logs/metrics.jsonl')
        with open(metrics_file, 'a') as f:
            f.write(json.dumps(metrics_data, ensure_ascii=False) + '\\n')
    
    def update_request_metrics(self, success=True, cost=0.0, response_time=0.0):
        """更新请求指标"""
        self.metrics['total_requests'] += 1
        self.metrics['last_request_time'] = datetime.now()
        
        if success:
            self.metrics['successful_requests'] += 1
        else:
            self.metrics['failed_requests'] += 1
        
        self.metrics['total_cost'] += cost
        
        # 更新平均响应时间
        total_time = (self.metrics['average_response_time'] * 
                     (self.metrics['total_requests'] - 1) + response_time)
        self.metrics['average_response_time'] = total_time / self.metrics['total_requests']
    
    def run_monitoring_cycle(self):
        """运行一次监控周期"""
        self.logger.info("开始监控周期...")
        
        # 收集指标
        system_metrics = self.collect_system_metrics()
        app_metrics = self.collect_app_metrics()
        
        # 检查告警
        alerts = self.check_alerts(system_metrics, app_metrics)
        
        # 记录指标
        self.log_metrics(system_metrics, app_metrics)
        
        # 输出状态
        print(f"🔍 监控报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   📊 请求统计: {app_metrics['total_requests']} 总计, {app_metrics['error_rate']:.2%} 错误率")
        print(f"   💰 累计成本: ${app_metrics['total_cost']:.2f}")
        print(f"   ⏱️  平均响应: {app_metrics['average_response_time']:.1f}秒")
        print(f"   🖥️  系统负载: CPU {system_metrics['cpu_percent']:.1f}%, 内存 {system_metrics['memory_percent']:.1f}%")
        
        # 处理告警
        if alerts:
            print("⚠️ 告警:")
            for alert in alerts:
                print(f"   🚨 {alert}")
                self.logger.warning(f"告警: {alert}")
        else:
            print("✅ 系统状态正常")
    
    def cleanup_old_logs(self):
        """清理旧日志"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config['log_retention_days'])
            log_dir = Path('logs')
            
            for log_file in log_dir.glob('*.log'):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    self.logger.info(f"清理旧日志文件: {log_file}")
        except Exception as e:
            self.logger.error(f"日志清理失败: {e}")
    
    def start_monitoring(self):
        """开始监控"""
        self.logger.info("启动生产环境监控...")
        
        try:
            while True:
                self.run_monitoring_cycle()
                
                # 定期清理日志
                if self.metrics['total_requests'] % 100 == 0:
                    self.cleanup_old_logs()
                
                # 等待下一个监控周期
                time.sleep(self.config['monitor_interval'])
                
        except KeyboardInterrupt:
            self.logger.info("监控停止")
        except Exception as e:
            self.logger.error(f"监控异常: {e}")

def main():
    """主函数"""
    print("🔍 ETH永续合约AI分析助手 - 生产环境监控")
    print("=" * 50)
    
    monitor = ProductionMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # 运行一次监控
        monitor.run_monitoring_cycle()
    else:
        # 持续监控
        monitor.start_monitoring()

if __name__ == '__main__':
    main()