#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆瓣到 Trakt 统一系统 - 主入口

集成所有功能：
1. 获取 Trakt 访问令牌
2. 从豆瓣抓取观影记录
3. 同步到 Trakt 账户
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """主函数"""
    print("=" * 70)
    print("豆瓣到 Trakt 统一系统")
    print("=" * 70)
    print("此系统将自动完成以下步骤:")
    print("1. 获取 Trakt 访问令牌")
    print("2. 从豆瓣抓取观影记录并生成 CSV")
    print("3. 将数据同步到 Trakt 账户")
    print("=" * 70)
    
    # 导入配置模块
    try:
        from unified_system.config import get_user_input
        from unified_system.orchestrator import run_unified_workflow
    except ImportError as e:
        print(f"导入模块失败: {e}")
        print("请确保在项目根目录运行此程序")
        return
    
    # 获取用户配置
    config = get_user_input()
    if not config:
        print("配置获取失败，程序终止")
        return
    
    # 确认信息
    print("\n" + "=" * 60)
    print("配置确认:")
    print("=" * 60)
    print(f"豆瓣用户ID: {config['douban']['user_id']}")
    print(f"起始日期: {config['douban']['start_date']}")
    print(f"CSV 输出: {config['douban']['csv_output']}")
    print(f"令牌文件: {config['trakt']['token_file']}")
    print(f"Dry-run 模式: {'是' if config['system']['dry_run'] else '否'}")
    print("=" * 60)
    
    # 确认继续
    confirm = input("\n是否继续? (y/N): ").strip().lower()
    if confirm != 'y':
        print("操作取消")
        return
    
    # 运行统一工作流程
    success = run_unified_workflow(config)
    
    if success:
        print("\n🎉 所有任务完成!")
        
        if config['system']['dry_run']:
            print("\n注意: 运行在干运行模式，未实际修改任何数据")
            print("如果要实际同步数据，请重新运行并禁用 dry-run 模式")
        else:
            print("\n数据已成功同步到 Trakt 账户")
            print(f"- 令牌文件: {config['trakt']['token_file']}")
            print(f"- 数据文件: {config['douban']['csv_output']}")
    else:
        print("\n❌ 工作流程执行失败")
        print("请检查错误信息并重试")

if __name__ == "__main__":
    main()