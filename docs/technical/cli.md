根据用户的不同需求，推荐以下命令：

  🎯 个人交易者（推荐）

  # 获取具体的入场/出场价格（你之前的需求）
  python main.py --trading-signal --symbol ETHUSDT --model gpt4o-mini

  # 30秒快速信号，成本<$0.01
  python main.py --mode quick --ultra-economy --symbol ETHUSDT

  # 最经济的日常使用
  python main.py --ultra-economy --symbol ETHUSDT

  💰 成本优化命令（日常使用）

  # 超经济模式：<$0.01 per analysis
  python main.py --ultra-economy --symbol ETHUSDT

  # 快速信号：<$0.005 per analysis  
  python main.py --mode quick --model gemini-flash --symbol ETHUSDT

  # 平衡模式：<$0.02 per analysis
  python main.py --trading-signal --model gpt4o-mini --symbol ETHUSDT

  🏆 高质量分析（重要决策时）

  # 最佳质量单模型分析
  python main.py --model gpt5-mini --symbol ETHUSDT

  # 多模型验证（最可靠，防AI幻觉）
  python main.py --enable-validation --symbol ETHUSDT

  # 快速验证模式
  python main.py --enable-validation --fast-validation --symbol ETHUSDT

  📊 不同分析模式

  # 交易信号模式（具体入场/出场价格）
  python main.py --mode signal --symbol ETHUSDT

  # 快速信号（30秒内）
  python main.py --mode quick --symbol ETHUSDT

  # 执行摘要格式
  python main.py --mode executive --symbol ETHUSDT

  # 深度研究分析（学术级）
  python main.py --mode research --symbol ETHUSDT

  ⚡ 最常用组合推荐

  # 1. 日常交易信号检查（最实用）
  python main.py --trading-signal --model gpt4o-mini --symbol ETHUSDT

  # 2. 紧急快速信号（最快最便宜）  
  python main.py --mode quick --ultra-economy --symbol ETHUSDT

  # 3. 重要决策验证（最可靠）
  python main.py --enable-validation --fast-validation --symbol ETHUSDT

  🆕 第一次使用建议

  # 1. 验证系统设置
  source venv/bin/activate
  python -c "from config import Settings; Settings.validate()"

  # 2. 测试交易信号模式
  python main.py --trading-signal --symbol ETHUSDT --model gpt4o-mini

  # 3. 如果满意，可以使用更经济的版本
  python main.py --ultra-economy --symbol ETHUSDT

  基于你之前的反馈（需要具体入场/出场价格），建议使用：
  python main.py --trading-signal --symbol ETHUSDT --model gpt4o-mini

  这个命令会给你：
  - 具体的买入/卖出价格
  - 止损位设置
  - 目标价位
  - 风险回报比
  - 仓位建议

  成本大约$0.01-0.02，比之前的$7.06节省95%以上！