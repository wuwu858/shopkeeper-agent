# eval/report.py

import json
from datetime import datetime
from pathlib import Path


def generate_report(results: dict, output_dir: Path = None):
    """生成评测报告"""

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": results["total"],
            "success_rate": results["success_rate"],
            "sql_accuracy": results["sql_accuracy"],
            "result_accuracy": results["result_accuracy"],
            "avg_time": results["avg_time"]
        },
        "details": results["details"]
    }

    # 打印摘要
    print("\n" + "=" * 50)
    print("📊 评测报告")
    print("=" * 50)
    print(f"总样本数: {report['summary']['total']}")
    print(f"成功率: {report['summary']['success_rate']:.2%}")
    print(f"SQL 正确率: {report['summary']['sql_accuracy']:.2%}")
    print(f"结果正确率: {report['summary']['result_accuracy']:.2%}")
    print(f"平均耗时: {report['summary']['avg_time']:.2f}s")
    print("=" * 50)

    # 按难度分类
    by_difficulty = {}
    for detail in results["details"]:
        # 这里需要从 question 中获取 difficulty
        pass

    # 保存报告
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        report_path = output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n📁 报告已保存: {report_path}")

    return report